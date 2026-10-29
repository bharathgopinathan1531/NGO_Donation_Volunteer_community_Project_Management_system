# API Reference (generated from OpenAPI)

**NGO Donation, Volunteer & Community Project Management System** v1.0.0 — 104 paths. Interactive docs: `/docs` (Swagger UI), `/redoc`, raw spec: `/openapi.json`.

Auth: `Authorization: Bearer <access_token>` on every endpoint except login/register/forgot/reset/refresh and `/health*`.


## Health

### `GET /health`
Liveness probe

**Responses:** 200 → ``

### `GET /health/ready`
Readiness probe (checks the database)

**Responses:** 200 → ``


## Authentication

### `POST /api/v1/auth/register`
Self-register (volunteer or donor)

**Request body:** `RegisterRequest`

| Field | Type | Required |
|---|---|---|
| email | string | yes |
| full_name | string | yes |
| password | string | yes |
| role | Role | no |

**Responses:** 201 → `UserOut`; 422 → `HTTPValidationError`

### `POST /api/v1/auth/login`
Login and receive access + refresh tokens

**Request body:** `LoginRequest`

| Field | Type | Required |
|---|---|---|
| email | string | yes |
| password | string | yes |

**Responses:** 200 → `TokenResponse`; 422 → `HTTPValidationError`

### `POST /api/v1/auth/refresh`
Exchange a refresh token for a new token pair (rotation)

**Request body:** `RefreshRequest`

| Field | Type | Required |
|---|---|---|
| refresh_token | string | yes |

**Responses:** 200 → `TokenResponse`; 422 → `HTTPValidationError`

### `POST /api/v1/auth/logout`
Revoke a refresh token

**Request body:** `RefreshRequest`

| Field | Type | Required |
|---|---|---|
| refresh_token | string | yes |

**Responses:** 200 → `Message`; 422 → `HTTPValidationError`

### `GET /api/v1/auth/me`
Current user

**Responses:** 200 → `UserOut`

### `POST /api/v1/auth/forgot-password`
Start the password reset workflow

**Request body:** `ForgotPasswordRequest`

| Field | Type | Required |
|---|---|---|
| email | string | yes |

**Responses:** 200 → `ForgotPasswordResponse`; 422 → `HTTPValidationError`

### `POST /api/v1/auth/reset-password`
Complete the password reset with the emailed token

**Request body:** `ResetPasswordRequest`

| Field | Type | Required |
|---|---|---|
| token | string | yes |
| new_password | string | yes |

**Responses:** 200 → `Message`; 422 → `HTTPValidationError`

### `POST /api/v1/auth/change-password`
Change own password

**Request body:** `ChangePasswordRequest`

| Field | Type | Required |
|---|---|---|
| current_password | string | yes |
| new_password | string | yes |

**Responses:** 200 → `Message`; 422 → `HTTPValidationError`


## Users

### `GET /api/v1/users`
List users

| Param | In | Type | Required |
|---|---|---|---|
| role | query | Role | null | no |
| is_active | query | boolean | null | no |
| search | query | string | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_UserOut_`; 422 → `HTTPValidationError`

### `POST /api/v1/users`
Create a user with any role

**Request body:** `UserCreate`

| Field | Type | Required |
|---|---|---|
| email | string | yes |
| full_name | string | yes |
| password | string | yes |
| role | Role | yes |

**Responses:** 201 → `UserOut`; 422 → `HTTPValidationError`

### `GET /api/v1/users/{user_id}`
Get User

| Param | In | Type | Required |
|---|---|---|---|
| user_id | path | integer | yes |

**Responses:** 200 → `UserOut`; 422 → `HTTPValidationError`

### `PATCH /api/v1/users/{user_id}`
Update User

| Param | In | Type | Required |
|---|---|---|---|
| user_id | path | integer | yes |

**Request body:** `UserUpdate`

| Field | Type | Required |
|---|---|---|
| full_name | string | null | no |
| role | Role | null | no |

**Responses:** 200 → `UserOut`; 422 → `HTTPValidationError`

### `POST /api/v1/users/{user_id}/activate`
Activate an account

| Param | In | Type | Required |
|---|---|---|---|
| user_id | path | integer | yes |

**Responses:** 200 → `UserOut`; 422 → `HTTPValidationError`

### `POST /api/v1/users/{user_id}/deactivate`
Deactivate an account (revokes refresh tokens)

| Param | In | Type | Required |
|---|---|---|---|
| user_id | path | integer | yes |

**Responses:** 200 → `UserOut`; 422 → `HTTPValidationError`


## Donors

### `POST /api/v1/donors`
Create a donor profile

**Request body:** `DonorCreate`

| Field | Type | Required |
|---|---|---|
| name | string | yes |
| donor_type | DonorType | no |
| email | string | null | no |
| phone | string | null | no |
| address | string | null | no |
| city | string | null | no |
| country | string | null | no |
| tax_id | string | null | no |
| contact_person | string | null | no |
| notes | string | null | no |
| status | DonorStatus | no |
| user_id | integer | null | no |

**Responses:** 201 → `DonorOut`; 422 → `HTTPValidationError`

### `GET /api/v1/donors`
Search and filter donors

| Param | In | Type | Required |
|---|---|---|---|
| search | query | string | null | no |
| donor_type | query | DonorType | null | no |
| status | query | DonorStatus | null | no |
| city | query | string | null | no |
| country | query | string | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_DonorOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/donors/me`
The donor profile linked to my account

**Responses:** 200 → `DonorOut`

### `GET /api/v1/donors/{donor_id}`
Get Donor

| Param | In | Type | Required |
|---|---|---|---|
| donor_id | path | integer | yes |

**Responses:** 200 → `DonorOut`; 422 → `HTTPValidationError`

### `PATCH /api/v1/donors/{donor_id}`
Update a donor profile

| Param | In | Type | Required |
|---|---|---|---|
| donor_id | path | integer | yes |

**Request body:** `DonorUpdate`

| Field | Type | Required |
|---|---|---|
| name | string | null | no |
| donor_type | DonorType | null | no |
| status | DonorStatus | null | no |
| email | string | null | no |
| phone | string | null | no |
| address | string | null | no |
| city | string | null | no |
| country | string | null | no |
| tax_id | string | null | no |
| contact_person | string | null | no |
| notes | string | null | no |

**Responses:** 200 → `DonorOut`; 422 → `HTTPValidationError`

### `GET /api/v1/donors/{donor_id}/donations`
Donation history of a donor

| Param | In | Type | Required |
|---|---|---|---|
| donor_id | path | integer | yes |
| status | query | DonationStatus | null | no |
| method | query | DonationMethod | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_DonationOut_`; 422 → `HTTPValidationError`


## Campaigns

### `POST /api/v1/campaigns`
Create a fundraising campaign (starts as draft)

**Request body:** `CampaignCreate`

| Field | Type | Required |
|---|---|---|
| title | string | yes |
| description | string | null | no |
| category | CampaignCategory | no |
| goal_amount | number | string | yes |
| start_date | string | yes |
| end_date | string | yes |
| manager_id | integer | null | no |

**Responses:** 201 → `CampaignOut`; 422 → `HTTPValidationError`

### `GET /api/v1/campaigns`
List Campaigns

| Param | In | Type | Required |
|---|---|---|---|
| search | query | string | null | no |
| status | query | CampaignStatus | null | no |
| category | query | CampaignCategory | null | no |
| manager_id | query | integer | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_CampaignOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/campaigns/{campaign_id}`
Get Campaign

| Param | In | Type | Required |
|---|---|---|---|
| campaign_id | path | integer | yes |

**Responses:** 200 → `CampaignOut`; 422 → `HTTPValidationError`

### `PATCH /api/v1/campaigns/{campaign_id}`
Update Campaign

| Param | In | Type | Required |
|---|---|---|---|
| campaign_id | path | integer | yes |

**Request body:** `CampaignUpdate`

| Field | Type | Required |
|---|---|---|
| title | string | null | no |
| description | string | null | no |
| category | CampaignCategory | null | no |
| goal_amount | number | string | null | no |
| start_date | string | null | no |
| end_date | string | null | no |
| manager_id | integer | null | no |

**Responses:** 200 → `CampaignOut`; 422 → `HTTPValidationError`

### `POST /api/v1/campaigns/{campaign_id}/activate`
Activate (or resume) a campaign

| Param | In | Type | Required |
|---|---|---|---|
| campaign_id | path | integer | yes |

**Responses:** 200 → `CampaignOut`; 422 → `HTTPValidationError`

### `POST /api/v1/campaigns/{campaign_id}/pause`
Pause an active campaign

| Param | In | Type | Required |
|---|---|---|---|
| campaign_id | path | integer | yes |

**Responses:** 200 → `CampaignOut`; 422 → `HTTPValidationError`

### `POST /api/v1/campaigns/{campaign_id}/close`
Close a campaign as completed

| Param | In | Type | Required |
|---|---|---|---|
| campaign_id | path | integer | yes |

**Responses:** 200 → `CampaignOut`; 422 → `HTTPValidationError`

### `POST /api/v1/campaigns/{campaign_id}/cancel`
Cancel a campaign

| Param | In | Type | Required |
|---|---|---|---|
| campaign_id | path | integer | yes |

**Responses:** 200 → `CampaignOut`; 422 → `HTTPValidationError`


## Donations

### `POST /api/v1/donations`
Record a donation

**Request body:** `DonationCreate`

| Field | Type | Required |
|---|---|---|
| donor_id | integer | yes |
| campaign_id | integer | yes |
| amount | number | string | yes |
| donation_date | string | yes |
| method | DonationMethod | yes |
| reference_number | string | yes |
| status | DonationStatus | no |
| notes | string | null | no |

**Responses:** 201 → `DonationOut`; 422 → `HTTPValidationError`

### `GET /api/v1/donations`
Donation history with filters

| Param | In | Type | Required |
|---|---|---|---|
| donor_id | query | integer | null | no |
| campaign_id | query | integer | null | no |
| status | query | DonationStatus | null | no |
| method | query | DonationMethod | null | no |
| search | query | string | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_DonationOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/donations/{donation_id}`
Get Donation

| Param | In | Type | Required |
|---|---|---|---|
| donation_id | path | integer | yes |

**Responses:** 200 → `DonationOut`; 422 → `HTTPValidationError`

### `PATCH /api/v1/donations/{donation_id}`
Edit a donation (financial fields only while pending)

| Param | In | Type | Required |
|---|---|---|---|
| donation_id | path | integer | yes |

**Request body:** `DonationUpdate`

| Field | Type | Required |
|---|---|---|
| amount | number | string | null | no |
| donation_date | string | null | no |
| method | DonationMethod | null | no |
| notes | string | null | no |

**Responses:** 200 → `DonationOut`; 422 → `HTTPValidationError`

### `GET /api/v1/donations/{donation_id}/receipt`
Receipt of a donation

| Param | In | Type | Required |
|---|---|---|---|
| donation_id | path | integer | yes |

**Responses:** 200 → `ReceiptOut`; 422 → `HTTPValidationError`

### `POST /api/v1/donations/{donation_id}/confirm`
Confirm a pending donation (adds it to the campaign total)

| Param | In | Type | Required |
|---|---|---|---|
| donation_id | path | integer | yes |

**Request body:** `Body_endpoint_api_v1_donations__donation_id__confirm_post`

| Field | Type | Required |
|---|---|---|
| reason | string | null | no |

**Responses:** 200 → `DonationOut`; 422 → `HTTPValidationError`

### `POST /api/v1/donations/{donation_id}/cancel`
Cancel a pending donation

| Param | In | Type | Required |
|---|---|---|---|
| donation_id | path | integer | yes |

**Request body:** `Body_endpoint_api_v1_donations__donation_id__cancel_post`

| Field | Type | Required |
|---|---|---|
| reason | string | null | no |

**Responses:** 200 → `DonationOut`; 422 → `HTTPValidationError`

### `POST /api/v1/donations/{donation_id}/reverse`
Reverse a confirmed donation (deducts from campaign total, voids receipt)

| Param | In | Type | Required |
|---|---|---|---|
| donation_id | path | integer | yes |

**Request body:** `Body_endpoint_api_v1_donations__donation_id__reverse_post`

| Field | Type | Required |
|---|---|---|
| reason | string | null | no |

**Responses:** 200 → `DonationOut`; 422 → `HTTPValidationError`

### `POST /api/v1/donations/{donation_id}/refund`
Refund a confirmed donation (deducts from campaign total, voids receipt)

| Param | In | Type | Required |
|---|---|---|---|
| donation_id | path | integer | yes |

**Request body:** `Body_endpoint_api_v1_donations__donation_id__refund_post`

| Field | Type | Required |
|---|---|---|
| reason | string | null | no |

**Responses:** 200 → `DonationOut`; 422 → `HTTPValidationError`


## Receipts

### `POST /api/v1/receipts`
Generate a receipt for a confirmed donation

**Request body:** `ReceiptCreate`

| Field | Type | Required |
|---|---|---|
| donation_id | integer | yes |

**Responses:** 201 → `ReceiptOut`; 422 → `HTTPValidationError`

### `GET /api/v1/receipts`
List Receipts

| Param | In | Type | Required |
|---|---|---|---|
| donor_id | query | integer | null | no |
| status | query | ReceiptStatus | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_ReceiptOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/receipts/donor/{donor_id}`
Receipts of a donor

| Param | In | Type | Required |
|---|---|---|---|
| donor_id | path | integer | yes |
| status | query | ReceiptStatus | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_ReceiptOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/receipts/by-number/{receipt_number}`
Get By Number

| Param | In | Type | Required |
|---|---|---|---|
| receipt_number | path | string | yes |

**Responses:** 200 → `ReceiptOut`; 422 → `HTTPValidationError`

### `GET /api/v1/receipts/{receipt_id}`
Get Receipt

| Param | In | Type | Required |
|---|---|---|---|
| receipt_id | path | integer | yes |

**Responses:** 200 → `ReceiptOut`; 422 → `HTTPValidationError`

### `GET /api/v1/receipts/{receipt_id}/pdf`
Download the receipt as a PDF

| Param | In | Type | Required |
|---|---|---|---|
| receipt_id | path | integer | yes |

**Responses:** 200; 422 → `HTTPValidationError`


## Volunteers

### `POST /api/v1/volunteers`
Register a volunteer (staff)

**Request body:** `VolunteerCreate`

| Field | Type | Required |
|---|---|---|
| full_name | string | yes |
| email | string | yes |
| phone | string | null | no |
| address | string | null | no |
| skills | list[string] | no |
| experience | string | null | no |
| availability | string | null | no |
| emergency_contact_name | string | null | no |
| emergency_contact_phone | string | null | no |
| emergency_contact_relation | string | null | no |
| user_id | integer | null | no |

**Responses:** 201 → `VolunteerOut`; 422 → `HTTPValidationError`

### `GET /api/v1/volunteers`
Search and filter volunteers

| Param | In | Type | Required |
|---|---|---|---|
| search | query | string | null | no |
| status | query | VolunteerStatus | null | no |
| skill | query | string | null | no |
| availability | query | string | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_VolunteerOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/volunteers/me`
My volunteer profile

**Responses:** 200 → `VolunteerOut`

### `POST /api/v1/volunteers/me`
Create my own volunteer profile

**Request body:** `VolunteerCreate`

| Field | Type | Required |
|---|---|---|
| full_name | string | yes |
| email | string | yes |
| phone | string | null | no |
| address | string | null | no |
| skills | list[string] | no |
| experience | string | null | no |
| availability | string | null | no |
| emergency_contact_name | string | null | no |
| emergency_contact_phone | string | null | no |
| emergency_contact_relation | string | null | no |
| user_id | integer | null | no |

**Responses:** 201 → `VolunteerOut`; 422 → `HTTPValidationError`

### `GET /api/v1/volunteers/{volunteer_id}`
Get Volunteer

| Param | In | Type | Required |
|---|---|---|---|
| volunteer_id | path | integer | yes |

**Responses:** 200 → `VolunteerOut`; 422 → `HTTPValidationError`

### `PATCH /api/v1/volunteers/{volunteer_id}`
Update a volunteer (own profile or staff)

| Param | In | Type | Required |
|---|---|---|---|
| volunteer_id | path | integer | yes |

**Request body:** `VolunteerUpdate`

| Field | Type | Required |
|---|---|---|
| full_name | string | null | no |
| phone | string | null | no |
| address | string | null | no |
| skills | list[string] | null | no |
| experience | string | null | no |
| availability | string | null | no |
| status | VolunteerStatus | null | no |
| emergency_contact_name | string | null | no |
| emergency_contact_phone | string | null | no |
| emergency_contact_relation | string | null | no |

**Responses:** 200 → `VolunteerOut`; 422 → `HTTPValidationError`


## Volunteer Assignments

### `POST /api/v1/assignments`
Assign a volunteer to a project (rejects overlapping assignments)

**Request body:** `AssignmentCreate`

| Field | Type | Required |
|---|---|---|
| volunteer_id | integer | yes |
| project_id | integer | yes |
| responsibility | string | yes |
| start_date | string | yes |
| end_date | string | yes |

**Responses:** 201 → `AssignmentOut`; 422 → `HTTPValidationError`

### `GET /api/v1/assignments`
Assignment history (volunteers see only their own)

| Param | In | Type | Required |
|---|---|---|---|
| volunteer_id | query | integer | null | no |
| project_id | query | integer | null | no |
| status | query | AssignmentStatus | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_AssignmentOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/assignments/{assignment_id}`
Get Assignment

| Param | In | Type | Required |
|---|---|---|---|
| assignment_id | path | integer | yes |

**Responses:** 200 → `AssignmentOut`; 422 → `HTTPValidationError`

### `PATCH /api/v1/assignments/{assignment_id}`
Update Assignment

| Param | In | Type | Required |
|---|---|---|---|
| assignment_id | path | integer | yes |

**Request body:** `AssignmentUpdate`

| Field | Type | Required |
|---|---|---|
| responsibility | string | null | no |
| start_date | string | null | no |
| end_date | string | null | no |

**Responses:** 200 → `AssignmentOut`; 422 → `HTTPValidationError`

### `POST /api/v1/assignments/{assignment_id}/status`
Activate, complete or cancel an assignment

| Param | In | Type | Required |
|---|---|---|---|
| assignment_id | path | integer | yes |

**Request body:** `AssignmentStatusChange`

| Field | Type | Required |
|---|---|---|
| status | AssignmentStatus | yes |

**Responses:** 200 → `AssignmentOut`; 422 → `HTTPValidationError`


## Attendance

### `POST /api/v1/attendance`
Record attendance and hours for an assignment day

**Request body:** `AttendanceCreate`

| Field | Type | Required |
|---|---|---|
| assignment_id | integer | yes |
| attendance_date | string | yes |
| status | AttendanceStatus | no |
| hours | number | string | no |
| notes | string | null | no |

**Responses:** 201 → `AttendanceOut`; 422 → `HTTPValidationError`

### `GET /api/v1/attendance`
List Attendance

| Param | In | Type | Required |
|---|---|---|---|
| assignment_id | query | integer | null | no |
| status | query | AttendanceStatus | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_AttendanceOut_`; 422 → `HTTPValidationError`

### `PATCH /api/v1/attendance/{attendance_id}`
Correct an attendance record

| Param | In | Type | Required |
|---|---|---|---|
| attendance_id | path | integer | yes |

**Request body:** `AttendanceUpdate`

| Field | Type | Required |
|---|---|---|
| status | AttendanceStatus | null | no |
| hours | number | string | null | no |
| notes | string | null | no |

**Responses:** 200 → `AttendanceOut`; 422 → `HTTPValidationError`


## Community Projects

### `POST /api/v1/projects`
Create a community project (starts in planning)

**Request body:** `ProjectCreate`

| Field | Type | Required |
|---|---|---|
| name | string | yes |
| description | string | null | no |
| objectives | string | null | no |
| location | string | null | no |
| start_date | string | yes |
| end_date | string | yes |
| budget | number | string | no |
| manager_id | integer | null | no |
| campaign_id | integer | null | no |

**Responses:** 201 → `ProjectDetail`; 422 → `HTTPValidationError`

### `GET /api/v1/projects`
List projects (volunteers see only projects they are assigned to)

| Param | In | Type | Required |
|---|---|---|---|
| search | query | string | null | no |
| status | query | ProjectStatus | null | no |
| manager_id | query | integer | null | no |
| campaign_id | query | integer | null | no |
| location | query | string | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_ProjectOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/projects/{project_id}`
Get Project

| Param | In | Type | Required |
|---|---|---|---|
| project_id | path | integer | yes |

**Responses:** 200 → `ProjectDetail`; 422 → `HTTPValidationError`

### `PATCH /api/v1/projects/{project_id}`
Update Project

| Param | In | Type | Required |
|---|---|---|---|
| project_id | path | integer | yes |

**Request body:** `ProjectUpdate`

| Field | Type | Required |
|---|---|---|
| name | string | null | no |
| description | string | null | no |
| objectives | string | null | no |
| location | string | null | no |
| start_date | string | null | no |
| end_date | string | null | no |
| budget | number | string | null | no |
| manager_id | integer | null | no |
| campaign_id | integer | null | no |

**Responses:** 200 → `ProjectDetail`; 422 → `HTTPValidationError`

### `POST /api/v1/projects/{project_id}/status`
Change status (activation requires approval)

| Param | In | Type | Required |
|---|---|---|---|
| project_id | path | integer | yes |

**Request body:** `ProjectStatusChange`

| Field | Type | Required |
|---|---|---|
| status | ProjectStatus | yes |

**Responses:** 200 → `ProjectDetail`; 422 → `HTTPValidationError`

### `GET /api/v1/projects/{project_id}/milestones`
Milestone tracking for a project

| Param | In | Type | Required |
|---|---|---|---|
| project_id | path | integer | yes |

**Responses:** 200 → `list[MilestoneOut]`; 422 → `HTTPValidationError`


## Project Approvals

### `POST /api/v1/projects/{project_id}/submit`
Submit a project for approval

| Param | In | Type | Required |
|---|---|---|---|
| project_id | path | integer | yes |

**Request body:** `SubmitForApproval | null`

**Responses:** 201 → `ApprovalOut`; 422 → `HTTPValidationError`

### `POST /api/v1/projects/{project_id}/approve`
Approve a submitted project

| Param | In | Type | Required |
|---|---|---|---|
| project_id | path | integer | yes |

**Request body:** `ApprovalDecision | null`

**Responses:** 200 → `ApprovalOut`; 422 → `HTTPValidationError`

### `POST /api/v1/projects/{project_id}/reject`
Reject a submitted project (comment required)

| Param | In | Type | Required |
|---|---|---|---|
| project_id | path | integer | yes |

**Request body:** `RejectDecision`

| Field | Type | Required |
|---|---|---|
| comments | string | yes |

**Responses:** 200 → `ApprovalOut`; 422 → `HTTPValidationError`

### `GET /api/v1/projects/{project_id}/approvals`
Approval history of a project

| Param | In | Type | Required |
|---|---|---|---|
| project_id | path | integer | yes |

**Responses:** 200 → `list[ApprovalOut]`; 422 → `HTTPValidationError`

### `GET /api/v1/approvals/pending`
Projects waiting for an approval decision

| Param | In | Type | Required |
|---|---|---|---|
| page | query | integer | no |
| page_size | query | integer | no |

**Responses:** 200 → `Page_ApprovalOut_`; 422 → `HTTPValidationError`


## Milestones

### `POST /api/v1/milestones`
Create Milestone

**Request body:** `MilestoneCreate`

| Field | Type | Required |
|---|---|---|
| project_id | integer | yes |
| title | string | yes |
| description | string | null | no |
| due_date | string | yes |

**Responses:** 201 → `MilestoneOut`; 422 → `HTTPValidationError`

### `GET /api/v1/milestones`
List milestones (overdue_only=true finds late ones)

| Param | In | Type | Required |
|---|---|---|---|
| project_id | query | integer | null | no |
| status | query | MilestoneStatus | null | no |
| overdue_only | query | boolean | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_MilestoneOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/milestones/{milestone_id}`
Get Milestone

| Param | In | Type | Required |
|---|---|---|---|
| milestone_id | path | integer | yes |

**Responses:** 200 → `MilestoneOut`; 422 → `HTTPValidationError`

### `PATCH /api/v1/milestones/{milestone_id}`
Update Milestone

| Param | In | Type | Required |
|---|---|---|---|
| milestone_id | path | integer | yes |

**Request body:** `MilestoneUpdate`

| Field | Type | Required |
|---|---|---|
| title | string | null | no |
| description | string | null | no |
| due_date | string | null | no |
| status | MilestoneStatus | null | no |

**Responses:** 200 → `MilestoneOut`; 422 → `HTTPValidationError`

### `DELETE /api/v1/milestones/{milestone_id}`
Delete Milestone

| Param | In | Type | Required |
|---|---|---|---|
| milestone_id | path | integer | yes |

**Responses:** 200 → `Message`; 422 → `HTTPValidationError`


## Tasks

### `POST /api/v1/tasks`
Create and assign a task

**Request body:** `TaskCreate`

| Field | Type | Required |
|---|---|---|
| milestone_id | integer | yes |
| title | string | yes |
| description | string | null | no |
| assignee_id | integer | null | no |
| priority | TaskPriority | no |
| deadline | string | yes |

**Responses:** 201 → `TaskOut`; 422 → `HTTPValidationError`

### `GET /api/v1/tasks`
List tasks (staff: all; others: their own)

| Param | In | Type | Required |
|---|---|---|---|
| milestone_id | query | integer | null | no |
| project_id | query | integer | null | no |
| assignee_id | query | integer | null | no |
| status | query | TaskStatus | null | no |
| priority | query | TaskPriority | null | no |
| overdue_only | query | boolean | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_TaskOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/tasks/overdue`
Overdue tasks

| Param | In | Type | Required |
|---|---|---|---|
| project_id | query | integer | null | no |
| assignee_id | query | integer | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_TaskOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/tasks/{task_id}`
Get Task

| Param | In | Type | Required |
|---|---|---|---|
| task_id | path | integer | yes |

**Responses:** 200 → `TaskOut`; 422 → `HTTPValidationError`

### `PATCH /api/v1/tasks/{task_id}`
Update task status / progress (assignees may update their own)

| Param | In | Type | Required |
|---|---|---|---|
| task_id | path | integer | yes |

**Request body:** `TaskUpdate`

| Field | Type | Required |
|---|---|---|
| title | string | null | no |
| description | string | null | no |
| assignee_id | integer | null | no |
| priority | TaskPriority | null | no |
| deadline | string | null | no |
| status | TaskStatus | null | no |
| progress | integer | null | no |

**Responses:** 200 → `TaskOut`; 422 → `HTTPValidationError`

### `DELETE /api/v1/tasks/{task_id}`
Delete Task

| Param | In | Type | Required |
|---|---|---|---|
| task_id | path | integer | yes |

**Responses:** 200 → `Message`; 422 → `HTTPValidationError`


## Expenses

### `POST /api/v1/expenses`
Submit a project expense

**Request body:** `ExpenseCreate`

| Field | Type | Required |
|---|---|---|
| project_id | integer | yes |
| category | ExpenseCategory | yes |
| amount | number | string | yes |
| expense_date | string | yes |
| description | string | yes |
| receipt_reference | string | null | no |
| attachment_url | string | null | no |

**Responses:** 201 → `ExpenseOut`; 422 → `HTTPValidationError`

### `GET /api/v1/expenses`
List expenses (users without finance access see their own)

| Param | In | Type | Required |
|---|---|---|---|
| project_id | query | integer | null | no |
| status | query | ExpenseStatus | null | no |
| category | query | ExpenseCategory | null | no |
| search | query | string | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_ExpenseOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/expenses/{expense_id}`
Get Expense

| Param | In | Type | Required |
|---|---|---|---|
| expense_id | path | integer | yes |

**Responses:** 200 → `ExpenseOut`; 422 → `HTTPValidationError`

### `PATCH /api/v1/expenses/{expense_id}`
Edit a not-yet-reviewed expense

| Param | In | Type | Required |
|---|---|---|---|
| expense_id | path | integer | yes |

**Request body:** `ExpenseUpdate`

| Field | Type | Required |
|---|---|---|
| category | ExpenseCategory | null | no |
| amount | number | string | null | no |
| expense_date | string | null | no |
| description | string | null | no |
| receipt_reference | string | null | no |
| attachment_url | string | null | no |

**Responses:** 200 → `ExpenseOut`; 422 → `HTTPValidationError`

### `POST /api/v1/expenses/{expense_id}/approve`
Approve an expense (finance only, budget-checked)

| Param | In | Type | Required |
|---|---|---|---|
| expense_id | path | integer | yes |

**Request body:** `ExpenseApprove | null`

**Responses:** 200 → `ExpenseOut`; 422 → `HTTPValidationError`

### `POST /api/v1/expenses/{expense_id}/reject`
Reject an expense (comment required)

| Param | In | Type | Required |
|---|---|---|---|
| expense_id | path | integer | yes |

**Request body:** `ExpenseReject`

| Field | Type | Required |
|---|---|---|
| comment | string | yes |

**Responses:** 200 → `ExpenseOut`; 422 → `HTTPValidationError`

### `POST /api/v1/expenses/{expense_id}/reimburse`
Mark an approved expense as reimbursed

| Param | In | Type | Required |
|---|---|---|---|
| expense_id | path | integer | yes |

**Responses:** 200 → `ExpenseOut`; 422 → `HTTPValidationError`


## Budgets

### `PUT /api/v1/budgets`
Define (or replace) a campaign or project budget

**Request body:** `BudgetSet`

| Field | Type | Required |
|---|---|---|
| scope | BudgetScope | yes |
| campaign_id | integer | null | no |
| project_id | integer | null | no |
| amount | number | string | yes |
| notes | string | null | no |

**Responses:** 200 → `BudgetOut`; 422 → `HTTPValidationError`

### `GET /api/v1/budgets`
List Budgets

| Param | In | Type | Required |
|---|---|---|---|
| scope | query | BudgetScope | null | no |
| page | query | integer | no |
| page_size | query | integer | no |

**Responses:** 200 → `Page_BudgetOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/budgets/utilization`
Budget utilization (remaining budget, overruns)

| Param | In | Type | Required |
|---|---|---|---|
| scope | query | BudgetScope | null | no |
| only_overruns | query | boolean | no |

**Responses:** 200 → `list[BudgetUtilization]`; 422 → `HTTPValidationError`

### `GET /api/v1/budgets/projects/{project_id}/utilization`
Project Utilization

| Param | In | Type | Required |
|---|---|---|---|
| project_id | path | integer | yes |

**Responses:** 200 → `BudgetUtilization`; 422 → `HTTPValidationError`

### `GET /api/v1/budgets/campaigns/{campaign_id}/utilization`
Campaign Utilization

| Param | In | Type | Required |
|---|---|---|---|
| campaign_id | path | integer | yes |

**Responses:** 200 → `BudgetUtilization`; 422 → `HTTPValidationError`


## Resources & Inventory

### `POST /api/v1/resources`
Register a resource (optional opening stock)

**Request body:** `ResourceCreate`

| Field | Type | Required |
|---|---|---|
| name | string | yes |
| category | ResourceCategory | yes |
| description | string | null | no |
| unit | string | no |
| initial_quantity | integer | no |
| low_stock_threshold | integer | no |

**Responses:** 201 → `ResourceOut`; 422 → `HTTPValidationError`

### `GET /api/v1/resources`
List Resources

| Param | In | Type | Required |
|---|---|---|---|
| category | query | ResourceCategory | null | no |
| search | query | string | null | no |
| low_stock_only | query | boolean | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_ResourceOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/resources/low-stock`
Low-stock alerts

**Responses:** 200 → `list[ResourceOut]`

### `GET /api/v1/resources/transactions`
Stock movement ledger / distribution history

| Param | In | Type | Required |
|---|---|---|---|
| resource_id | query | integer | null | no |
| project_id | query | integer | null | no |
| transaction_type | query | StockTransactionType | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_StockTransactionOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/resources/{resource_id}`
Get Resource

| Param | In | Type | Required |
|---|---|---|---|
| resource_id | path | integer | yes |

**Responses:** 200 → `ResourceOut`; 422 → `HTTPValidationError`

### `PATCH /api/v1/resources/{resource_id}`
Update Resource

| Param | In | Type | Required |
|---|---|---|---|
| resource_id | path | integer | yes |

**Request body:** `ResourceUpdate`

| Field | Type | Required |
|---|---|---|
| name | string | null | no |
| category | ResourceCategory | null | no |
| description | string | null | no |
| unit | string | null | no |
| low_stock_threshold | integer | null | no |

**Responses:** 200 → `ResourceOut`; 422 → `HTTPValidationError`

### `POST /api/v1/resources/{resource_id}/stock-in`
Stock In

| Param | In | Type | Required |
|---|---|---|---|
| resource_id | path | integer | yes |

**Request body:** `StockMovement`

| Field | Type | Required |
|---|---|---|
| quantity | integer | yes |
| reason | string | null | no |
| reference | string | null | no |

**Responses:** 201 → `StockTransactionOut`; 422 → `HTTPValidationError`

### `POST /api/v1/resources/{resource_id}/stock-out`
Stock out (never below zero)

| Param | In | Type | Required |
|---|---|---|---|
| resource_id | path | integer | yes |

**Request body:** `StockOutMovement`

| Field | Type | Required |
|---|---|---|
| quantity | integer | yes |
| reason | string | yes |
| reference | string | null | no |

**Responses:** 201 → `StockTransactionOut`; 422 → `HTTPValidationError`


## Resource Allocations

### `POST /api/v1/resource-allocations`
Allocate stock to a project

**Request body:** `AllocationCreate`

| Field | Type | Required |
|---|---|---|
| resource_id | integer | yes |
| project_id | integer | yes |
| quantity | integer | yes |
| notes | string | null | no |

**Responses:** 201 → `AllocationOut`; 422 → `HTTPValidationError`

### `GET /api/v1/resource-allocations`
Allocation / distribution history

| Param | In | Type | Required |
|---|---|---|---|
| resource_id | query | integer | null | no |
| project_id | query | integer | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_AllocationOut_`; 422 → `HTTPValidationError`


## Beneficiaries

### `POST /api/v1/beneficiaries`
Register a beneficiary

**Request body:** `BeneficiaryCreate`

| Field | Type | Required |
|---|---|---|
| full_name | string | yes |
| category | BeneficiaryCategory | yes |
| age | integer | null | no |
| gender | string | null | no |
| phone | string | null | no |
| address | string | null | no |
| national_id | string | null | no |
| notes | string | null | no |
| project_ids | list[integer] | no |

**Responses:** 201 → `BeneficiaryOut`; 422 → `HTTPValidationError`

### `GET /api/v1/beneficiaries`
List beneficiaries (sensitive fields redacted for unprivileged roles)

| Param | In | Type | Required |
|---|---|---|---|
| search | query | string | null | no |
| category | query | BeneficiaryCategory | null | no |
| project_id | query | integer | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_BeneficiaryOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/beneficiaries/{beneficiary_id}`
Get Beneficiary

| Param | In | Type | Required |
|---|---|---|---|
| beneficiary_id | path | integer | yes |

**Responses:** 200 → `BeneficiaryOut`; 422 → `HTTPValidationError`

### `PATCH /api/v1/beneficiaries/{beneficiary_id}`
Update Beneficiary

| Param | In | Type | Required |
|---|---|---|---|
| beneficiary_id | path | integer | yes |

**Request body:** `BeneficiaryUpdate`

| Field | Type | Required |
|---|---|---|
| full_name | string | null | no |
| category | BeneficiaryCategory | null | no |
| age | integer | null | no |
| gender | string | null | no |
| phone | string | null | no |
| address | string | null | no |
| national_id | string | null | no |
| notes | string | null | no |

**Responses:** 200 → `BeneficiaryOut`; 422 → `HTTPValidationError`

### `POST /api/v1/beneficiaries/{beneficiary_id}/projects/{project_id}`
Map a beneficiary to a project

| Param | In | Type | Required |
|---|---|---|---|
| beneficiary_id | path | integer | yes |
| project_id | path | integer | yes |

**Responses:** 200 → `BeneficiaryOut`; 422 → `HTTPValidationError`

### `DELETE /api/v1/beneficiaries/{beneficiary_id}/projects/{project_id}`
Remove a beneficiary from a project

| Param | In | Type | Required |
|---|---|---|---|
| beneficiary_id | path | integer | yes |
| project_id | path | integer | yes |

**Responses:** 200 → `BeneficiaryOut`; 422 → `HTTPValidationError`


## Beneficiary Assistance

### `POST /api/v1/assistance`
Record assistance given to a beneficiary

**Request body:** `AssistanceCreate`

| Field | Type | Required |
|---|---|---|
| beneficiary_id | integer | yes |
| project_id | integer | yes |
| resource_id | integer | null | no |
| assistance_type | string | yes |
| quantity | integer | no |
| distribution_date | string | yes |
| description | string | null | no |

**Responses:** 201 → `AssistanceOut`; 422 → `HTTPValidationError`

### `GET /api/v1/assistance`
Assistance history

| Param | In | Type | Required |
|---|---|---|---|
| beneficiary_id | query | integer | null | no |
| project_id | query | integer | null | no |
| resource_id | query | integer | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_AssistanceOut_`; 422 → `HTTPValidationError`


## Impact Tracking

### `POST /api/v1/impact/updates`
Submit a project impact update

**Request body:** `ImpactUpdateCreate`

| Field | Type | Required |
|---|---|---|
| project_id | integer | yes |
| beneficiaries_served | integer | null | no |
| volunteer_hours | number | string | null | no |
| resources_distributed | integer | null | no |
| funds_utilized | number | string | null | no |
| milestones_achieved | integer | null | no |
| notes | string | null | no |

**Responses:** 201 → `ImpactUpdateOut`; 422 → `HTTPValidationError`

### `GET /api/v1/impact/updates`
Impact update history

| Param | In | Type | Required |
|---|---|---|---|
| project_id | query | integer | null | no |
| page | query | integer | no |
| page_size | query | integer | no |

**Responses:** 200 → `Page_ImpactUpdateOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/impact/summary`
Live impact metrics (organisation-wide or per project)

| Param | In | Type | Required |
|---|---|---|---|
| project_id | query | integer | null | no |

**Responses:** 200 → `ImpactSummary`; 422 → `HTTPValidationError`


## Notifications

### `GET /api/v1/notifications`
My notifications

| Param | In | Type | Required |
|---|---|---|---|
| unread_only | query | boolean | no |
| type | query | NotificationType | null | no |
| page | query | integer | no |
| page_size | query | integer | no |

**Responses:** 200 → `Page_NotificationOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/notifications/unread-count`
Unread Count

**Responses:** 200 → `UnreadCount`

### `POST /api/v1/notifications/read-all`
Mark all my notifications as read

**Responses:** 200 → `Message`

### `POST /api/v1/notifications/generate`
Scan for deadlines, overdue milestones, low stock, pending expenses, closing campaigns, overruns

**Responses:** 200 → `GenerationResult`

### `POST /api/v1/notifications/{notification_id}/read`
Mark Read

| Param | In | Type | Required |
|---|---|---|---|
| notification_id | path | integer | yes |

**Responses:** 200 → `NotificationOut`; 422 → `HTTPValidationError`

### `POST /api/v1/notifications/{notification_id}/unread`
Mark Unread

| Param | In | Type | Required |
|---|---|---|---|
| notification_id | path | integer | yes |

**Responses:** 200 → `NotificationOut`; 422 → `HTTPValidationError`


## Dashboard

### `GET /api/v1/dashboard`
All dashboard metrics (computed from database records)

**Responses:** 200 → `DashboardOverview`

### `GET /api/v1/dashboard/donations`
Total and confirmed donations

**Responses:** 200 → `DonationMetrics`

### `GET /api/v1/dashboard/campaigns`
Active campaigns and goal achievement

**Responses:** 200 → `CampaignMetrics`

### `GET /api/v1/dashboard/volunteers`
Volunteers and hours

**Responses:** 200 → `VolunteerMetrics`

### `GET /api/v1/dashboard/projects`
Active projects, pending approvals, budget utilization

**Responses:** 200 → `ProjectMetrics`

### `GET /api/v1/dashboard/expenses`
Pending expense approvals

**Responses:** 200 → `ExpenseMetrics`

### `GET /api/v1/dashboard/resources`
Resource stock levels

**Responses:** 200 → `ResourceMetrics`

### `GET /api/v1/dashboard/beneficiaries`
Beneficiaries registered and served

**Responses:** 200 → `BeneficiaryMetrics`


## Reports

### `GET /api/v1/reports/donation-summary`
Donation summary grouped by campaign / donor / method / status / month

| Param | In | Type | Required |
|---|---|---|---|
| group_by | query | string | no |
| campaign_id | query | integer | null | no |
| status | query | DonationStatus | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| export | query | boolean | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `ReportPage`; 422 → `HTTPValidationError`

### `GET /api/v1/reports/campaign-performance`
Campaign Performance

| Param | In | Type | Required |
|---|---|---|---|
| campaign_id | query | integer | null | no |
| status | query | CampaignStatus | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| export | query | boolean | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `ReportPage`; 422 → `HTTPValidationError`

### `GET /api/v1/reports/expenses`
Expense Report

| Param | In | Type | Required |
|---|---|---|---|
| project_id | query | integer | null | no |
| campaign_id | query | integer | null | no |
| status | query | ExpenseStatus | null | no |
| category | query | ExpenseCategory | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| export | query | boolean | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `ReportPage`; 422 → `HTTPValidationError`

### `GET /api/v1/reports/budget-utilization`
Budget Utilization

| Param | In | Type | Required |
|---|---|---|---|
| scope | query | BudgetScope | null | no |
| only_overruns | query | boolean | no |
| export | query | boolean | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `ReportPage`; 422 → `HTTPValidationError`

### `GET /api/v1/reports/volunteer-contribution`
Volunteer Contribution

| Param | In | Type | Required |
|---|---|---|---|
| project_id | query | integer | null | no |
| status | query | VolunteerStatus | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| export | query | boolean | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `ReportPage`; 422 → `HTTPValidationError`

### `GET /api/v1/reports/project-progress`
Project Progress

| Param | In | Type | Required |
|---|---|---|---|
| project_id | query | integer | null | no |
| status | query | ProjectStatus | null | no |
| campaign_id | query | integer | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| export | query | boolean | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `ReportPage`; 422 → `HTTPValidationError`

### `GET /api/v1/reports/resource-distribution`
Resource Distribution

| Param | In | Type | Required |
|---|---|---|---|
| project_id | query | integer | null | no |
| resource_id | query | integer | null | no |
| category | query | ResourceCategory | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| export | query | boolean | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `ReportPage`; 422 → `HTTPValidationError`

### `GET /api/v1/reports/beneficiary-impact`
Beneficiary Impact

| Param | In | Type | Required |
|---|---|---|---|
| group_by | query | string | no |
| project_id | query | integer | null | no |
| category | query | BeneficiaryCategory | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| export | query | boolean | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `ReportPage`; 422 → `HTTPValidationError`


## Audit Logs

### `GET /api/v1/audit-logs`
Audit trail (actor, action, entity, timestamp, change details)

| Param | In | Type | Required |
|---|---|---|---|
| actor_id | query | integer | null | no |
| action | query | string | null | no |
| entity | query | string | null | no |
| entity_id | query | integer | null | no |
| date_from | query | string | null | no |
| date_to | query | string | null | no |
| page | query | integer | no |
| page_size | query | integer | no |
| sort_by | query | string | null | no |
| order | query | string | no |

**Responses:** 200 → `Page_AuditLogOut_`; 422 → `HTTPValidationError`

### `GET /api/v1/audit-logs/{log_id}`
Get Log

| Param | In | Type | Required |
|---|---|---|---|
| log_id | path | integer | yes |

**Responses:** 200 → `AuditLogOut`; 422 → `HTTPValidationError`
