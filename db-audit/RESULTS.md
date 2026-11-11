# CDD actions - stored in the local DB? (field by field)

Kaduna AZM build `org.egov.azm.gombe` 2.2.122 (the `-db` build), emulator `HCM_Beneficiary_ID` (`emulator-5554`, device time zone Asia/Calcutta), CDD `dis-qa-oct29`, Fangwani Health Clinic / Rigan Ori. 2026-11-10.

**Method.** One record per case. Each action was done in the app as a CDD user would. After each action, that record was read from the app's own local database (SQLite, encrypted with SQLCipher) through the app's **DB** card. The DB card is the Drift DB viewer, and its query editor runs SQL. The SQL used for each check is saved with its answer in `artifacts/db-audit/queries/`. Screenshots are in `artifacts/db-audit/evidence/`. How to rerun: [README.md](README.md).

Status: **Saved** = the value entered is in the column; **Missing** = entered but not found; **Not stored** = shown in the form but kept nowhere; **Correctly not saved** = nothing stored, and nothing should be; **N/A** = the field was not shown (its condition was not met), or was left blank where optional. Cases 1-5 ran on 10 Nov 2026, Cases 6-10 on 11 Nov.

## Case 1 - Household 1: registration, then eligibility checklist leading to a referral

Household head `QAID-DB1-H Test` (ID 152062311161), child `QAID-DB1-C1 Test` (ID 152320332491). Registered 14:31-14:35; checklist and referral 15:16-15:29.

### Registration (household, head, child)

| Screen | Field | Entered | Table.column | Stored | Status |
| --- | --- | --- | --- | --- | --- |
| Beneficiary Location | administrativeArea | Rigan Ori | household.additional_fields `administrativeArea`; address.locality_boundary_code | Rigan Ori; ADMIN_NI_01_01_06_02_13_RIGAN_ORI | Saved |
| Beneficiary Location | latLng | emulator fix 10.5222, 7.4388 | household.latitude / longitude; address.latitude / longitude / location_accuracy (household and head rows) | 10.5221983, 7.4387983, accuracy 5.0 | Saved |
| Beneficiary Location | typeOfAddress (hidden, default PERMANENT) | - | household.additional_fields `typeOfAddress`; address.type | PERMANENT; 0 | Saved (default) |
| Beneficiary Location | addressLine1, addressLine2, landmark, pincode | hidden | address.address_line1 / address_line2 / landmark / pincode | - | N/A (hidden) |
| Caregiver Consent | consentToParticipate | Yes | household.additional_fields `caregiverConsent` | TRUE | Saved |
| Household Details | dateOfRegistration (read-only, today) | 10 Nov 2026 | project_beneficiary.date_of_registration | 1794301374626 (2026-11-10 14:32) | Saved |
| Household Details | memberCount | 5 | household.member_count; household.additional_fields `memberCount` | 5; 5 | Saved |
| Household Details | childrenCount, pregnantWomenCount | hidden | - | - | N/A (hidden) |
| Beneficiary Details (head) | nameOfIndividual | QAID-DB1-H | name.given_name | QAID-DB1-H | Saved |
| Beneficiary Details (head) | familyname | Test | name.family_name | Test | Saved |
| Beneficiary Details (head) | isHeadOfFamily | ticked | household_member.is_head_of_household | 1 | Saved |
| Beneficiary Details (head) | identifiers (hidden; the pool ID) | - | identifier.identifier_type / identifier_id | UNIQUE_BENEFICIARY_ID / 152062311161 (= card) | Saved |
| Beneficiary Details (head) | dobPicker | age 30 years | individual.date_of_birth; household_member.additional_fields `dateOfBirth`, `ageInMonths` | 10/11/1996; 10/11/1996, 360 | Saved |
| Beneficiary Details (head) | gender | Female | individual.gender; household_member.additional_fields `gender` | 1; FEMALE | Saved |
| Beneficiary Details (head) | phone | left blank (optional) | individual.mobile_number | null | N/A (blank) |
| Child's Details | nameOfIndividual / familyname | QAID-DB1-C1 / Test | name.given_name / family_name | QAID-DB1-C1 / Test | Saved |
| Child's Details | dobPicker | age 2 years | individual.date_of_birth; household_member.additional_fields `ageInMonths` | 10/11/2024; 24 | Saved |
| Child's Details | gender | Female | individual.gender | 1 | Saved |
| Child's Details | height (shown from 12 months) | 85 | individual.additional_fields `height` | "85" | Saved |
| Child's Details | identifiers | - | identifier | UNIQUE_BENEFICIARY_ID / 152320332491 (= card = success screen's Token ID) | Saved |
| Child's Details | (membership) | - | household_member (is_head 0, same household); project_beneficiary | rows present | Saved |

### Eligibility checklist -> Refer Beneficiary

The checklist itself saves nothing on Submit; its answers are carried to the referral, which stores them. The referral is stored in **h_f_referral**; the `referral` table stays empty (0 rows), and no `task` row is made.

| Screen | Field | Entered | Table.column | Stored | Status |
| --- | --- | --- | --- | --- | --- |
| Eligibility Assessment | ec1 (allergy to azithromycin) | Yes | h_f_referral.additional_fields `ec1Value` | YES | Saved |
| Eligibility Assessment | ec2 (liver / renal) | No | `ec2Value` | NO | Saved |
| Eligibility Assessment | ec3 (recent antibiotics) | No | `ec3Value` | NO | Saved |
| Eligibility Assessment | ec4 (chronic illness; shown when ec3 = No) | No | `ec4Value` | NO | Saved |
| Eligibility Assessment | ec5 (SP or CTX in 28 days) | No | `ec5Value` | NO | Saved |
| Eligibility Assessment | malariaVaccine | Yes | `malariaVaccineReceived` | YES | Saved |
| Eligibility Assessment | malariaVaccineDate (shown when Yes) | 02 Nov 2026 | `malariaVaccineLastDate` | 1793557800000 = 2026-11-02 00:00 IST | Saved |
| Eligibility Assessment | smc | Yes | `smcReceived` | YES | Saved |
| Eligibility Assessment | smcDate (shown when Yes) | 05 Nov 2026 | `smcLastDate` | 1793817000000 = 2026-11-05 00:00 IST | Saved |
| Eligibility Assessment | polio | No | `polioReceived` | NO | Saved |
| Eligibility Assessment | polioDate | not shown | - | no key | N/A |
| Eligibility Assessment | measlesRubella | No | `measlesRubellaReceived` | NO | Saved |
| Eligibility Assessment | measlesRubellaDate | not shown | - | no key | N/A |
| Refer Beneficiary | administrativeArea (prefilled) | Rigan Ori | h_f_referral.locality_code; additional_fields `localityCode`, `administrativeArea` | ADMIN_NI_..._RIGAN_ORI; Rigan Ori | Saved |
| Refer Beneficiary | referredBy (prefilled) | community distributor | additional_fields `referredBy` | the CDD's user UUID | Saved |
| Refer Beneficiary | healthFacility | Fangwani health clinic | h_f_referral.project_facility_id | PF-2026-06-10-068438 | Saved |
| (from the record) | child | QAID-DB1-C1 | h_f_referral.name, beneficiary_id, referral_code; additional_fields `nameOfReferral`, `nameOfHouseholdHead`, `gender`, `ageInMonths`, `latitude`, `longitude`, `referralCycle`, `dateOfEvaluation` | QAID-DB1-C1 Test, 152320332491, the individual's reference; ... | Saved |

**Points for the dev / QA:**
1. The referral reason is stored as **SICK** (h_f_referral.symptom, `referralReasons`, `referralSymptom`), but this referral came from ec1 = Yes (allergy to azithromycin). Is SICK intended for every checklist referral?
2. The SMC date is stored as `smcLastDate` (epoch milliseconds, local midnight) in h_f_referral.additional_fields, not as `smc_date` (the name in the pilot test list).
3. `flow` = `smcDone` is stored on the referral.

## Case 2 - Household 2: registration, then eligibility checklist leading to a successful delivery

Household head `QAID-DB2-H Test` (ID 152169182291), child `QAID-DB2-C1 Test` (ID 152113181641). Registered 16:14-16:19 (the same form as Case 1; its registration rows were not queried again - Cases 2-4 check the checklist and its outcome); checklist and delivery 16:20-16:28.

The checklist again saves nothing on Submit ("going to 'To Administer'"). Its answers are carried through Beneficiary Details -> Record Round Dose -> Delivery Details, and stored with the delivery in **task** (one row, status ADMINISTRATION_SUCCESS) and **task_resource** (one row).

| Screen | Field | Entered | Table.column | Stored | Status |
| --- | --- | --- | --- | --- | --- |
| Eligibility Assessment | ec1-ec5 | No, No, No, No (ec4 shown), No | task.additional_fields `ec1Value`-`ec5Value` | NO x5 | Saved |
| Eligibility Assessment | malariaVaccine | No | `malariaVaccineReceived` | NO | Saved |
| Eligibility Assessment | malariaVaccineDate | not shown | - | no key | N/A |
| Eligibility Assessment | smc / smcDate | Yes / 06 Nov 2026 | `smcReceived` / `smcLastDate` | YES / 1793903400000 = 2026-11-06 00:00 IST | Saved |
| Eligibility Assessment | polio / polioDate | Yes / 03 Nov 2026 | `polioReceived` / `polioLastDate` | YES / 1793644200000 = 2026-11-03 00:00 IST | Saved |
| Eligibility Assessment | measlesRubella | No | `measlesRubellaReceived` | NO | Saved |
| Eligibility Assessment | measlesRubellaDate | not shown | - | no key | N/A |
| Delivery Details | dateOfRegistration ("Date of delivery", read-only) | 10 Nov 2026 | task.additional_fields `administrationStartTime` / `administrationEndTime` | 2026-11-10 16:25 / 16:27 IST | Saved (as times) |
| Delivery Details | resourceCard - product | AZM | task_resource.product_variant_id | PVAR-2025-01-03-000003 | Saved |
| Delivery Details | resourceCard - Quantity Distributed | 8 (prefilled) | task_resource.quantity | "8" | Saved |
| Delivery Details | (delivered) | - | task_resource.is_delivered; task.status | 1; ADMINISTRATION_SUCCESS | Saved |
| Delivery Details | deliveryComment | Delivery Successful | task.additional_fields `deliveryComment` | SUCCESSFUL_DELIVERY | Saved |
| Delivery Details | deliveryComment | Delivery Successful | **task_resource.delivery_comment** | **null** | **Missing in this column** (kept in task.additional_fields only) |
| (from the record) | child, household | - | task.additional_fields `beneficiaryId`, `childName`, `ageInMonths`, `gender`, `height`, `headName`, `memberCount`, `householdClientReferenceId`, `individualClientReferenceId`, `doseIndex` 1, `cycleIndex` 2, `deliveryStrategy` DIRECT, `dateOfRegistration` | as entered | Saved |

**Points for the dev / QA:**
1. `task_resource.delivery_comment` is empty although a delivery comment was chosen; the value is only in `task.additional_fields.deliveryComment`. Is the column meant to be filled?
2. Dates use different formats in one record: `smcLastDate` / `polioLastDate` are epoch milliseconds, `dateOfRegistration` in the task is a text timestamp ("2026-11-10 16:25:46.421183"), project_beneficiary.date_of_registration is epoch milliseconds, and individual.date_of_birth is "dd/MM/yyyy".
3. On both paths the checklist's Submit saves nothing by itself; the live form config shows only a navigation there, and the answers are stored with the referral or delivery. So a checklist completed and then abandoned (Back, app killed) should leave no record of its answers. This comes from the config and is not yet tested by abandoning one.

## Case 3 - Household 3: registration, then eligibility checklist -> ineligible (ec5 = Yes)

Household head `QAID-DB3-H Test` (ID 161123211722), child `QAID-DB3-C1 Test` (ID 152132223152). Registered 16:34-16:38; checklist 16:38-16:41. The popup read "going to 'Ineligible flow'".

This is the one checklist outcome that saves at the checklist itself: **task**, one row, status **INELIGIBLE**, and no task_resource. The child's card then reads "Ineligible".

| Screen | Field | Entered | Table.column | Stored | Status |
| --- | --- | --- | --- | --- | --- |
| Eligibility Assessment | ec1-ec4 | No (ec4 shown) | task.additional_fields `ec1`-`ec4` | NO x4 | Saved |
| Eligibility Assessment | ec5 (SP or CTX in 28 days) | Yes | `ec5` | YES | Saved |
| Eligibility Assessment | malariaVaccine / malariaVaccineDate | Yes / 04 Nov 2026 | `malariaVaccine` / `malariaVaccineDate` | YES / "2026-11-04 00:00:00.000" | Saved |
| Eligibility Assessment | smc, polio, measlesRubella | No, No, No | `smc`, `polio`, `measlesRubella` | NO, NO, NO | Saved |
| Eligibility Assessment | smcDate, polioDate, measlesRubellaDate | not shown | - | no keys | N/A |
| (from the record) | child, household | - | `beneficiaryId`, `childName`, `ageInMonths`, `gender`, `headName`, `memberCount`, `householdClientReferenceId`, `individualClientReferenceId` | as entered | Saved |

**Point for the dev / QA - the same answers are stored three different ways:**

| | Delivery (Case 2: task) and referral (Cases 1, 4: h_f_referral) | Ineligible (Case 3: task) |
| --- | --- | --- |
| Question keys | `ec1Value` ... `ec5Value` | `ec1` ... `ec5` |
| Intervention keys | `malariaVaccineReceived`, `smcReceived`, `polioReceived`, `measlesRubellaReceived` | `malariaVaccine`, `smc`, `polio`, `measlesRubella` |
| Date keys | `malariaVaccineLastDate`, `smcLastDate`, `polioLastDate` | `malariaVaccineDate` (and presumably `smcDate`, `polioDate`) |
| Date format | epoch milliseconds (local midnight) | text "yyyy-MM-dd HH:mm:ss.SSS" |
| Height | in the delivery task | not stored |

A report or sync consumer reading these keys must handle both shapes.

## Case 4 - Household 4: referral with the SMC and polio dates of Case 2

Household head `QAID-DB4-H Test` (ID 161211153713), child `QAID-DB4-C1 Test` (ID 152229141615). Registered 16:45-16:49; checklist and referral 16:49-16:54. Same trigger as Case 1 (ec1 = Yes), and the interventions of Case 2. Stored in **h_f_referral** (one row, facility PF-2026-06-10-068438, symptom SICK); "Referral recorded successfully, ID-152229141615".

| Field | Entered | h_f_referral.additional_fields | Case 2 (delivery, task.additional_fields) | Status |
| --- | --- | --- | --- | --- |
| ec1 / ec2-ec5 | Yes / No x4 | `ec1Value` YES, `ec2Value`-`ec5Value` NO | (No x5) | Saved |
| malariaVaccine | No | `malariaVaccineReceived` NO | NO | Saved |
| smc / smcDate | Yes / 06 Nov 2026 | `smcReceived` YES / `smcLastDate` 1793903400000 | YES / 1793903400000 | Saved - **identical to Case 2** |
| polio / polioDate | Yes / 03 Nov 2026 | `polioReceived` YES / `polioLastDate` 1793644200000 | YES / 1793644200000 | Saved - **identical to Case 2** |
| measlesRubella | No | `measlesRubellaReceived` NO | NO | Saved |

The same dates are stored the same way by the referral and by the delivery: epoch milliseconds at local midnight (06 Nov 2026 00:00 IST, 03 Nov 2026 00:00 IST), with the same key names. The referral reason is SICK again (point 1 of Case 1).

## Case 5 - Household 5: caregiver consent No

10 Nov 19:27-19:30. Searched `QAID-DB5-H` -> Register New Beneficiary -> location -> Care giver's consent **No**, Enter Reason "QA test - consent refused" -> Submit -> "Data recorded successfully". Stored: **household** (1 row) and its **address**; no household_member, individual, name or project_beneficiary row. The name typed in search is not stored.

| Screen | Field | Entered | Table.column | Stored | Status |
| --- | --- | --- | --- | --- | --- |
| Beneficiary Location | administrativeArea | Rigan Ori | household.additional_fields `administrativeArea`; address.locality_boundary_code | Rigan Ori; ADMIN_NI_01_01_06_02_13_RIGAN_ORI | Saved |
| Beneficiary Location | latLng | emulator fix | household.latitude / longitude; address.location_accuracy | 10.5221983, 7.4387983; 5.0 | Saved |
| Beneficiary Location | typeOfAddress (hidden) | - | household.additional_fields `typeOfAddress`; address.type | PERMANENT; 0 | Saved (default) |
| Caregiver Consent | consentToParticipate | No | household.additional_fields `caregiverConsent` | FALSE | Saved |
| Caregiver Consent | negativeConsentReason (shown for No) | QA test - consent refused | household.additional_fields `negativeConsentReason` | QA test - consent refused | Saved |
| (outcome) | - | - | household_member / individual / name / project_beneficiary | 0 rows each | As expected |

**Point for the dev:** the refused household is saved with `member_count` 1, `memberCount` "1" and `isHeadOfFamily` "true", although nobody is registered. Should it be 0 and no head flag?

## Case 6 - Household 6: Unable to Deliver

Household head `QAID-DB6-H Test` (ID 161161018202), child `QAID-DB6-C1 Test` (ID 158181318102). The registration run started 10 Nov 19:34 stalled while the PC slept and saved the head on 11 Nov at 10:00; the child was added 10:03-10:06. On the child's card, **Unable To Deliver** sits beside Dose, so it is offered before any checklist. Reason **Beneficiary absent**, comment "QA test - absent" -> Proceed -> "the beneficiary will be reported as 'Absent'. This action cannot be changed later" -> Submit (10:09). The card then reads "Beneficiary Absent" and offers no Dose.

| Screen | Field | Entered | Table.column | Stored | Status |
| --- | --- | --- | --- | --- | --- |
| Unable to Deliver | reason (screen marks it *) | Beneficiary absent | task.status | BENEFICIARY_ABSENT | Saved (as the status only) |
| Unable to Deliver | latLng | auto, 5.00 meters | address (related to the task) latitude / longitude / location_accuracy | 10.5221983, 7.4387983, 5.0 | Saved |
| Unable to Deliver | comment | QA test - absent | task.additional_fields `comment` | QA test - absent | Saved |
| (outcome) | - | - | task_resource | 0 rows | As expected |
| (from the record) | child, household | - | task.additional_fields `beneficiaryId`, `childName`, `ageInMonths`, `gender`, `headName`, `memberCount`, `cycleIndex` 2, `flow` smcDone | as entered | Saved |

**Point for the dev:** the reason is kept only as the task status; there is no reason key, and `actual_start_date` / `actual_end_date` are null (the time is only in `client_created_time`).

## Case 9 - Household 9: SMC answer changed from Yes to No, then delivery

Household head `QAID-DB9-H Test` (ID 152382324713), child `QAID-DB9-C1 Test` (ID 158221616161). 11 Nov: registered 10:17-10:21; checklist and delivery 10:24-10:35. Checklist all No, SMC **Yes** with Last Date Received 05 Nov 2026, then SMC changed to **No** (the date field disappears), polio and measles No -> "To Administer" -> Record Round Dose -> Delivery Successful. Stored in **task** (ADMINISTRATION_SUCCESS) and **task_resource**.

| Field | Entered | task.additional_fields | Stored | Status |
| --- | --- | --- | --- | --- |
| ec1-ec5, malariaVaccine, polio, measlesRubella | No | `ec1Value`-`ec5Value`, `malariaVaccineReceived`, `polioReceived`, `measlesRubellaReceived` | NO | Saved |
| smc | Yes, then No | `smcReceived` | NO | Saved (the last answer) |
| smcDate | 05 Nov 2026, then hidden | `smcLastDate` | **no key** | Correctly not saved - the earlier date is dropped |
| Delivery: date, resource, comment | today; AZM 8; Delivery Successful | `administrationStartTime` / `EndTime` 10:32 / 10:35; task_resource AZM "8" delivered; `deliveryComment` SUCCESSFUL_DELIVERY | as entered | Saved |
| deliveryComment | Delivery Successful | **task_resource.delivery_comment** | **null** | **Missing in this column** (as Case 2) |

## Case 7 - Redose (the Case 9 child, 5 minutes after its delivery)

On 11 Nov the **Redose** button of Case 2's child (delivered 10 Nov 16:27) is greyed out: the form config disables it when `isRedoseWindowExpired(task)` is true (the window length is in the app code). On the Case 9 child, at 10:40 (delivery 10:35), Redose was enabled: Redose Details -> Date of Redose 11 Nov 2026 (prefilled), AZM 8 (prefilled), Reason **Others** -> the Comments box appears -> "QA test" -> Submit -> "Data recorded Successfully" (10:41). The card then shows "Redose Completed" and Redose is greyed out.

| Field | Entered | Table.column | Stored | Status |
| --- | --- | --- | --- | --- |
| dateOfRedose | 11 Nov 2026 (prefilled) | task.additional_fields `dateOfRedose` | "2026-11-11 10:40:15.079749" (time the form opened) | Saved |
| resourceCard | AZM, 8 | task_resource product_variant_id / quantity / is_delivered | PVAR-2025-01-03-000003 / "8" / 1 | Saved |
| reasonForRedose | Others | `reasonForRedose` | OTHERS | Saved |
| redoseComments (shown for Others) | QA test | `redoseComments` | QA test | Saved |
| (record) | - | a **new** task: status, `taskType`; task_resource.delivery_comment | **VISITED**, REDOSE; "REDOSE" | Saved; the delivery task is unchanged |

"QA test - redose" was typed; only "QA test" reached the field (adb typing, not the app). **Point for the dev:** a given redose is stored with status **VISITED**, not ADMINISTRATION_SUCCESS; and its task_resource.delivery_comment is filled ("REDOSE") while a normal delivery leaves it null.

## Case 10 - Abandoned checklist

Child `QAID-DB10-C1 Test` (ID 152016141611), added to household 9 (10:48-10:51). Dose -> Eligibility Assessment -> ec1 No, ec2 No -> the app's **Back** (10:52). No "discard changes?" warning; the card still reads "Not Administered" with Dose.

| Check | Table | Rows for this child | Status |
| --- | --- | --- | --- |
| task | task (by project beneficiary and by beneficiary ID) | 0 | Correctly not saved |
| referral | h_f_referral, referral | 0, 0 | Correctly not saved |
| checklist | service (all rows) | 0 | Correctly not saved |
| registration | project_beneficiary | 1 (from Add Members) | as expected |

## Case 8 - Revisit and edit household 1

Reopened household 1 (Case 1) on 11 Nov 11:15. The overview shows the saved values: head QAID-DB1-H Test, Rigan Ori, 5 members, consent True, head FEMALE 30y, child "Beneficiary Referred". There is no edit for the household itself, only Edit Individual. The head's **Edit Individual** form (titled "Child's Details") shows QAID-DB1-H / Test, 10 Nov 1996, 30 y 0 m, Female, mobile empty. The test number first given (11 digits) is refused: "Mobile number should be 10 digits." The user then gave a 10-digit test number (ending 3803) -> Next -> Submit (11:43) -> "Data recorded Successfully", Token ID 152062311161.

| Check | Before (11 Nov 11:00) | After (11:43) | Status |
| --- | --- | --- | --- |
| individual.mobile_number | null | the number entered (ending 3803) | Saved |
| individual row | 9bc9ef40..., 1 name, 1 identifier | the same row; no new individual (363 in all), name or identifier | Saved (updated, not duplicated) |
| client_modified_time | 10 Nov 14:33 | 11 Nov 11:43 | changes |
| audit_modified_time | 10 Nov 14:33 | 10 Nov 14:33 | **unchanged** |
| row_version | null | null | **unchanged** |
| individual.additional_fields | cycleIndexStamp | + `identifiers` "UNIQUE_BENEFICIARY_ID,152062311161" | new key |
| household_member | - | untouched | - |

**Points for the dev:** row_version and audit_modified_time do not change on a local edit (only client_modified_time); the edit adds an `identifiers` key; the head's edit form is titled "Child's Details".

## Run notes (11 Nov)

- The Case 6 registration started 10 Nov 19:34 stalled while the PC slept and finished the head on 11 Nov 10:00; the child was then added by `flows/add-child.yaml`.
- Claude Code's Maestro MCP server (`maestro mcp`, a java process) restarted three times and held the device, so `maestro hierarchy` hung. It was stopped each time; `scripts/screen.py` now gives up after 90 s with that hint.
