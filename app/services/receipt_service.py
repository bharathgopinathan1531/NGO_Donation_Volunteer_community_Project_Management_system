from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, BusinessRuleError
from app.core.permissions import Permission, has_permission
from app.db.session import transaction
from app.models.donation import Donation
from app.models.receipt import Receipt
from app.models.user import User
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.donation_repository import DonationRepository
from app.repositories.donor_repository import DonorRepository
from app.repositories.receipt_repository import ReceiptRepository
from app.services.audit_service import AuditService
from app.utils.date_utils import utcnow
from app.utils.enums import DonationStatus, ReceiptStatus
from app.utils.pagination import PaginationParams
from app.utils.receipt_number import generate_receipt_number
from app.utils.sorting import SortParams


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_simple_pdf(lines: list[tuple[int, str]]) -> bytes:
    """Dependency-free single-page PDF (Helvetica) - enough for a printable receipt."""
    content = ["BT"]
    y = 740
    for size, text in lines:
        content.append(f"/F1 {size} Tf 1 0 0 1 72 {y} Tm ({_pdf_escape(text)}) Tj")
        y -= size + 10
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode()
    return bytes(out)


class ReceiptService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ReceiptRepository(db)
        self.donations = DonationRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ commands
    def issue(self, actor: User, donation_id: int) -> Receipt:
        with transaction(self.db):
            donation = self.donations.get(donation_id, for_update=True)
            if not donation:
                raise NotFoundError("Donation not found")
            if donation.status != DonationStatus.CONFIRMED:
                raise BusinessRuleError(
                    f"Receipts can only be issued for confirmed donations (this donation is '{donation.status.value}')"
                )
            existing = self.repo.get_by_donation(donation.id)
            if existing:
                raise ConflictError(f"A receipt ({existing.receipt_number}) already exists for this donation")
            donor = DonorRepository(self.db).get(donation.donor_id)
            campaign = CampaignRepository(self.db).get(donation.campaign_id)
            number = generate_receipt_number()
            while self.repo.get_by_number(number):
                number = generate_receipt_number()
            receipt = self.repo.add(
                Receipt(
                    receipt_number=number, donation_id=donation.id, donor_id=donation.donor_id, amount=donation.amount,
                    issued_by=actor.id,
                    meta={
                        "donor_name": donor.name if donor else None, "donor_email": donor.email if donor else None,
                        "campaign_title": campaign.title if campaign else None, "payment_method": donation.method.value,
                        "donation_reference": donation.reference_number, "donation_date": donation.donation_date.isoformat(),
                    },
                )
            )
            self.audit.log(actor, "receipt.issued", "receipt", receipt.id, {"receipt_number": number, "donation_id": donation.id, "amount": donation.amount})
        return receipt

    def void_for_donation(self, actor: User | None, donation: Donation, reason: str) -> Receipt | None:
        """Called (inside the donation's transaction) when a donation is reversed or refunded."""
        receipt = self.repo.get_by_donation(donation.id)
        if receipt and receipt.status == ReceiptStatus.ISSUED:
            receipt.status = ReceiptStatus.VOID
            receipt.voided_at = utcnow()
            receipt.void_reason = reason[:255]
            self.audit.log(actor, "receipt.voided", "receipt", receipt.id, {"receipt_number": receipt.receipt_number, "reason": reason})
        return receipt

    # ------------------------------------------------------------------ queries
    def _own_donor_id(self, actor: User) -> int | None:
        donor = DonorRepository(self.db).get_by_user_id(actor.id)
        return donor.id if donor else None

    def _assert_access(self, actor: User, receipt: Receipt) -> None:
        if has_permission(actor.role, Permission.RECEIPTS_READ):
            return
        if has_permission(actor.role, Permission.RECEIPTS_READ_OWN) and receipt.donor_id == self._own_donor_id(actor):
            return
        raise ForbiddenError("You do not have access to this receipt")

    def get(self, actor: User, receipt_id: int) -> Receipt:
        receipt = self.repo.get(receipt_id)
        if not receipt:
            raise NotFoundError("Receipt not found")
        self._assert_access(actor, receipt)
        return receipt

    def get_by_number(self, actor: User, number: str) -> Receipt:
        receipt = self.repo.get_by_number(number)
        if not receipt:
            raise NotFoundError("Receipt not found")
        self._assert_access(actor, receipt)
        return receipt

    def for_donation(self, actor: User, donation_id: int) -> Receipt:
        receipt = self.repo.get_by_donation(donation_id)
        if not receipt:
            raise NotFoundError("No receipt exists for this donation")
        self._assert_access(actor, receipt)
        return receipt

    def list_receipts(self, actor: User, params: PaginationParams, sort: SortParams, *, donor_id: int | None, status: ReceiptStatus | None):
        if not has_permission(actor.role, Permission.RECEIPTS_READ):
            own = self._own_donor_id(actor)
            if own is None or (donor_id is not None and donor_id != own):
                raise ForbiddenError("You can only list your own receipts")
            donor_id = own
        return self.repo.list_receipts(params, sort, donor_id=donor_id, status=status)

    def pdf(self, actor: User, receipt_id: int) -> tuple[bytes, str]:
        receipt = self.get(actor, receipt_id)
        meta = receipt.meta or {}
        lines = [
            (20, "DONATION RECEIPT" + ("  -  VOID" if receipt.status == ReceiptStatus.VOID else "")),
            (12, f"Receipt No: {receipt.receipt_number}"),
            (12, f"Issued: {receipt.issued_at:%Y-%m-%d %H:%M} UTC"),
            (12, f"Donor: {meta.get('donor_name', '-')}"),
            (12, f"Campaign: {meta.get('campaign_title', '-')}"),
            (12, f"Amount: {receipt.amount}"),
            (12, f"Payment method: {meta.get('payment_method', '-')}"),
            (12, f"Donation reference: {meta.get('donation_reference', '-')}"),
            (12, f"Donation date: {meta.get('donation_date', '-')}"),
            (10, "Thank you for your generous support."),
        ]
        if receipt.status == ReceiptStatus.VOID:
            lines.append((10, f"Voided: {receipt.void_reason or ''}"))
        return build_simple_pdf(lines), f"{receipt.receipt_number}.pdf"
