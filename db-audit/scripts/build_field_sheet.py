"""Build db-audit/CDD-field-capture.xlsx: every CDD form field, captured in the
local DB or not, per case.

    python db-audit/scripts/build_field_sheet.py

(Not with -I: openpyxl is in the user's site-packages, which -I skips.)

Field facts (label, type, mandatory, conditional, parent) come from the live
form config (db-audit/config/formconfig-kaduna-20261102.json, logged by the
app from Kaduna UAT) and its English labels (config/localization-en.json).
What was entered and what the DB holds comes from OBS below - each row read
from the app's local DB on 2026-11-10 (RESULTS.md; the SQL and answers are in
artifacts/db-audit/queries/). Fields of the CDD screens no case has used yet
are listed as Not tested.
"""
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "CDD-field-capture.xlsx")

# The CDD's screens, in the order a CDD meets them: (flow, page, screen name).
SCREENS = [
    ("HOUSEHOLD", "beneficiaryLocation", "Beneficiary Location"),
    ("HOUSEHOLD", "caregiverConsent", "Caregiver Consent"),
    ("HOUSEHOLD", "householdDetails", "Household Details"),
    ("HOUSEHOLD", "beneficiaryDetails", "Beneficiary Details (head)"),
    ("ADD_MEMBER", "beneficiaryDetails", "Child's Details (Add Members)"),
    ("CHECKLIST", "eligibilityChecklist", "Eligibility Assessment"),
    ("REFER_BENEFICIARY", "referBeneficiary", "Refer Beneficiary"),
    ("DELIVERY", "DeliveryDetails", "Delivery Details"),
    ("REDOSE", "RedoseDetails", "Redose Details"),
    ("UNABLETODELIVER", "unableToDeliver", "Unable To Deliver"),
]

CASES = {
    1: "Case 1 - HH1 registration, checklist -> referral (child QAID-DB1-C1 152320332491)",
    2: "Case 2 - HH2 checklist -> successful delivery (child QAID-DB2-C1 152113181641)",
    3: "Case 3 - HH3 checklist -> ineligible, ec5 = Yes (child QAID-DB3-C1 152132223152)",
    4: "Case 4 - HH4 checklist -> referral with Case 2's SMC / polio dates (child QAID-DB4-C1 152229141615)",
    5: "Case 5 - Consent No (household QAID-DB5-H)",
    6: "Case 6 - Unable to Deliver (child QAID-DB6-C1 158181318102)",
    7: "Case 7 - Redose (child QAID-DB9-C1 158221616161, after its Case 9 delivery)",
    8: "Case 8 - Revisit and edit household 1 (head QAID-DB1-H 152062311161)",
    9: "Case 9 - SMC Yes + date changed to No, then delivery (child QAID-DB9-C1 158221616161)",
    10: "Case 10 - Abandoned checklist (child QAID-DB10-C1 152016141611)",
}

# What each case did and where it was stored - the Cases sheet (RESULTS.md).
# (case, status, action, household head (ID), child (ID), when, stored in, result / what to check)
CASE_INFO = [
    (1, "Done", "New household (head + 1 child); checklist ec1 = Yes -> Refer Beneficiary",
     "QAID-DB1-H Test (152062311161)", "QAID-DB1-C1 Test (152320332491)",
     "Registered 14:31-14:35; checklist and referral 15:16-15:29",
     "household, address, individual, name, identifier, household_member, project_beneficiary; h_f_referral (1 row). referral table 0 rows, no task",
     "Every field entered is captured. Referral reason stored as SICK although the trigger was ec1 (allergy)"),
    (2, "Done", "New household; checklist all No, SMC + polio Yes with dates -> Record Round Dose -> Delivery Successful",
     "QAID-DB2-H Test (152169182291)", "QAID-DB2-C1 Test (152113181641)",
     "Registered 16:14-16:19; checklist and delivery 16:20-16:28",
     "task (1 row, ADMINISTRATION_SUCCESS), task_resource (1 row)",
     "Captured, except task_resource.delivery_comment: null although Delivery Successful was chosen"),
    (3, "Done", "New household; checklist ec5 = Yes, malaria vaccine Yes with date -> Ineligible",
     "QAID-DB3-H Test (161123211722)", "QAID-DB3-C1 Test (152132223152)",
     "Registered 16:34-16:38; checklist 16:38-16:41",
     "task (1 row, INELIGIBLE), no task_resource",
     "Captured, but under other keys (ec1..ec5, smc, ...) and with a text date - see Findings"),
    (4, "Done", "New household; checklist ec1 = Yes, SMC 06 Nov and polio 03 Nov (as Case 2) -> Refer Beneficiary",
     "QAID-DB4-H Test (161211153713)", "QAID-DB4-C1 Test (152229141615)",
     "Registered 16:45-16:49; checklist and referral 16:49-16:54",
     "h_f_referral (1 row)",
     "Captured; SMC and polio dates stored exactly as in Case 2's delivery"),
    (5, "Done", "New household: searched QAID-DB5-H -> Register -> location -> Caregiver Consent No, reason \"QA test - consent refused\" -> Submit",
     "QAID-DB5-H (typed in search only - not stored)", "-", "19:27-19:30",
     "household (1 row) and its address; no household_member, individual, name or project_beneficiary",
     "Captured: caregiverConsent FALSE and the reason. Registration stops at the household. member_count 1 and isHeadOfFamily true are stored although no one is registered"),
    (6, "Done", "New household + child; on the child's card Unable To Deliver (offered beside Dose, before any checklist) -> Beneficiary absent, comment \"QA test - absent\" -> Proceed -> Submit",
     "QAID-DB6-H Test (161161018202)", "QAID-DB6-C1 Test (158181318102)",
     "11 Nov: head saved 10:00 (the 10 Nov 19:34 run stalled while the PC slept), child 10:03-10:06, Unable to Deliver 10:08-10:09",
     "task (1 row, BENEFICIARY_ABSENT) and an address row for its location; no task_resource",
     "Captured: the reason as the task status, the comment, the location. The card then reads Beneficiary Absent and offers no Dose"),
    (7, "Done", "Case 2's child (delivered 10 Nov): Redose greyed out on 11 Nov. Then on the Case 9 child, 5 minutes after its delivery: Redose -> reason Others -> comment -> Submit",
     "QAID-DB9-H Test (152382324713)", "QAID-DB9-C1 Test (158221616161)", "11 Nov 10:40-10:41",
     "a new task (VISITED, taskType REDOSE) + task_resource (delivery_comment REDOSE); the delivery task is unchanged",
     "Captured: date, resource, reason, comment. The card reads Redose Completed. Status VISITED to check"),
    (8, "Done", "Reopened household 1 (Case 1): checked the overview and the head's Edit Individual form, added the head's mobile number (a 10-digit test number from the user, ending 3803) -> Next -> Submit",
     "QAID-DB1-H Test (152062311161)", "-", "11 Nov: opened 11:15-11:17; edit submitted 11:43",
     "individual (same row updated)",
     "Saved values come back; mobile number captured in the same row. An 11-digit number is refused (exactly 10 digits). row_version / audit_modified_time unchanged"),
    (9, "Done", "New household + child; checklist all No, SMC Yes with 05 Nov, then SMC changed to No; Record Round Dose -> Delivery Successful",
     "QAID-DB9-H Test (152382324713)", "QAID-DB9-C1 Test (158221616161)", "11 Nov: registered 10:17-10:21; checklist and delivery 10:24-10:35",
     "task (1 row, ADMINISTRATION_SUCCESS), task_resource (1 row)",
     "smcReceived NO and no smcLastDate - the date picked before the change is dropped (correct). task_resource.delivery_comment null again"),
    (10, "Done", "Child QAID-DB10-C1 added to household 9; Dose -> checklist ec1 No, ec2 No -> the app's Back",
     "QAID-DB9-H Test (152382324713)", "QAID-DB10-C1 Test (152016141611)", "11 Nov: child added 10:48-10:51; checklist left 10:52",
     "nothing: no task, h_f_referral, referral or service row",
     "Correctly not saved. No discard warning on Back; the card still offers Dose"),
]

CAP, NOT, NA, NT = "Captured", "Not captured", "Not applicable", "Not tested"
AS = "Correctly not saved"
STATUSES = [CAP, NOT, AS, NA, NT]

HFR = "h_f_referral.additional_fields"
TAF = "task.additional_fields"

# (case, flow, page, fieldName, entered, table, column / key, stored in DB, status, notes)
OBS = [
    # ---- Case 1: registration (household, head, child) --------------------------------
    ("1", "HOUSEHOLD", "beneficiaryLocation", "administrativeArea", "Rigan Ori",
     "household; address", "additional_fields.administrativeArea; locality_boundary_code",
     "Rigan Ori; ADMIN_NI_01_01_06_02_13_RIGAN_ORI", CAP, "address.locality_boundary_name is null"),
    ("1", "HOUSEHOLD", "beneficiaryLocation", "latLng", "GPS fix 10.5222, 7.4388 (emulator)",
     "household; address", "latitude, longitude; latitude, longitude, location_accuracy",
     "10.5221983, 7.4387983; accuracy 5.0 (household row and head's row)", CAP, ""),
    ("1", "HOUSEHOLD", "beneficiaryLocation", "addressLine1", "(hidden)", "address", "address_line1", "-", NA, "Hidden on this form"),
    ("1", "HOUSEHOLD", "beneficiaryLocation", "addressLine2", "(hidden)", "address", "address_line2", "-", NA, "Hidden on this form"),
    ("1", "HOUSEHOLD", "beneficiaryLocation", "landmark", "(hidden)", "address", "landmark", "-", NA, "Hidden on this form"),
    ("1", "HOUSEHOLD", "beneficiaryLocation", "pincode", "(hidden)", "address", "pincode", "-", NA, "Hidden on this form"),
    ("1", "HOUSEHOLD", "beneficiaryLocation", "typeOfAddress", "(hidden; default PERMANENT)",
     "household; address", "additional_fields.typeOfAddress; type", "PERMANENT; 0", CAP, "Default value, not shown to the CDD"),
    ("1", "HOUSEHOLD", "caregiverConsent", "consentToParticipate", "Yes",
     "household", "additional_fields.caregiverConsent", "TRUE", CAP, ""),
    ("1", "HOUSEHOLD", "caregiverConsent", "negativeConsentReason", "(not shown: consent Yes)",
     "household", "additional_fields.negativeConsentReason", "-", NA, "Shown only for consent No - tested in Case 5"),
    ("1", "HOUSEHOLD", "householdDetails", "dateOfRegistration", "10 Nov 2026 (read-only, today)",
     "project_beneficiary", "date_of_registration", "1794301374626 = 10 Nov 2026 14:32 IST", CAP, "Epoch milliseconds"),
    ("1", "HOUSEHOLD", "householdDetails", "childrenCount", "(hidden)", "-", "-", "-", NA, "Hidden on this form"),
    ("1", "HOUSEHOLD", "householdDetails", "pregnantWomenCount", "(hidden)", "-", "-", "-", NA, "Hidden on this form"),
    ("1", "HOUSEHOLD", "householdDetails", "memberCount", "5",
     "household", "member_count; additional_fields.memberCount", "5; 5", CAP, ""),
    ("1", "HOUSEHOLD", "beneficiaryDetails", "nameOfIndividual", "QAID-DB1-H", "name", "given_name", "QAID-DB1-H", CAP, ""),
    ("1", "HOUSEHOLD", "beneficiaryDetails", "familyname", "Test", "name", "family_name", "Test", CAP, ""),
    ("1", "HOUSEHOLD", "beneficiaryDetails", "isHeadOfFamily", "Ticked (default)",
     "household_member", "is_head_of_household", "1", CAP, ""),
    ("1", "HOUSEHOLD", "beneficiaryDetails", "identifiers", "(hidden; from the ID pool)",
     "identifier", "identifier_type; identifier_id", "UNIQUE_BENEFICIARY_ID; 152062311161 (= card)", CAP, "Set by the app"),
    ("1", "HOUSEHOLD", "beneficiaryDetails", "dobPicker", "Age 30 years",
     "individual; household_member", "date_of_birth; additional_fields.dateOfBirth, ageInMonths",
     "10/11/1996; 10/11/1996, 360", CAP, "Date as dd/MM/yyyy"),
    ("1", "HOUSEHOLD", "beneficiaryDetails", "gender", "Female",
     "individual; household_member", "gender; additional_fields.gender", "1; FEMALE", CAP, "individual.gender is an enum (1 = female)"),
    ("1", "HOUSEHOLD", "beneficiaryDetails", "phone", "(left blank - optional)", "individual", "mobile_number", "null", NA, "Not entered"),
    ("1", "HOUSEHOLD", "beneficiaryDetails", "scanner", "(hidden)", "-", "-", "-", NA, "Hidden on this form"),
    ("1", "ADD_MEMBER", "beneficiaryDetails", "nameOfIndividual", "QAID-DB1-C1", "name", "given_name", "QAID-DB1-C1", CAP, ""),
    ("1", "ADD_MEMBER", "beneficiaryDetails", "familyname", "Test", "name", "family_name", "Test", CAP, ""),
    ("1", "ADD_MEMBER", "beneficiaryDetails", "identifiers", "(hidden; from the ID pool)",
     "identifier", "identifier_type; identifier_id", "UNIQUE_BENEFICIARY_ID; 152320332491 (= card = Token ID)", CAP, "Set by the app"),
    ("1", "ADD_MEMBER", "beneficiaryDetails", "dobPicker", "Age 2 years",
     "individual; household_member", "date_of_birth; additional_fields.ageInMonths", "10/11/2024; 24", CAP, ""),
    ("1", "ADD_MEMBER", "beneficiaryDetails", "gender", "Female", "individual", "gender", "1", CAP, ""),
    ("1", "ADD_MEMBER", "beneficiaryDetails", "height", "85", "individual", "additional_fields.height", "\"85\"", CAP,
     "Shown from 12 months of age; stored as text"),
    ("1", "ADD_MEMBER", "beneficiaryDetails", "phone", "(not shown: not the head)", "individual", "mobile_number", "-", NA, "Shown for the head only"),
    ("1", "ADD_MEMBER", "beneficiaryDetails", "scanner", "(hidden)", "-", "-", "-", NA, "Hidden on this form"),
    # ---- Case 1: checklist -> referral (stored in h_f_referral) ---------------------------
    ("1", "CHECKLIST", "eligibilityChecklist", "ec1", "Yes", "h_f_referral", "additional_fields.ec1Value", "YES", CAP, "Triggers the referral"),
    ("1", "CHECKLIST", "eligibilityChecklist", "ec2", "No", "h_f_referral", "additional_fields.ec2Value", "NO", CAP, ""),
    ("1", "CHECKLIST", "eligibilityChecklist", "ec3", "No", "h_f_referral", "additional_fields.ec3Value", "NO", CAP, ""),
    ("1", "CHECKLIST", "eligibilityChecklist", "ec4", "No", "h_f_referral", "additional_fields.ec4Value", "NO", CAP, ""),
    ("1", "CHECKLIST", "eligibilityChecklist", "ec5", "No", "h_f_referral", "additional_fields.ec5Value", "NO", CAP, ""),
    ("1", "CHECKLIST", "eligibilityChecklist", "malariaVaccine", "Yes", "h_f_referral", "additional_fields.malariaVaccineReceived", "YES", CAP, ""),
    ("1", "CHECKLIST", "eligibilityChecklist", "malariaVaccineDate", "02 Nov 2026", "h_f_referral",
     "additional_fields.malariaVaccineLastDate", "1793557800000 = 02 Nov 2026 00:00 IST", CAP, "Epoch milliseconds"),
    ("1", "CHECKLIST", "eligibilityChecklist", "smc", "Yes", "h_f_referral", "additional_fields.smcReceived", "YES", CAP, ""),
    ("1", "CHECKLIST", "eligibilityChecklist", "smcDate", "05 Nov 2026", "h_f_referral",
     "additional_fields.smcLastDate", "1793817000000 = 05 Nov 2026 00:00 IST", CAP, "Key is smcLastDate (not smc_date)"),
    ("1", "CHECKLIST", "eligibilityChecklist", "polio", "No", "h_f_referral", "additional_fields.polioReceived", "NO", CAP, ""),
    ("1", "CHECKLIST", "eligibilityChecklist", "polioDate", "(not shown: polio No)", "h_f_referral", "additional_fields.polioLastDate", "no key", NA, ""),
    ("1", "CHECKLIST", "eligibilityChecklist", "measlesRubella", "No", "h_f_referral", "additional_fields.measlesRubellaReceived", "NO", CAP, ""),
    ("1", "CHECKLIST", "eligibilityChecklist", "measlesRubellaDate", "(not shown: No)", "h_f_referral", "additional_fields.measlesRubellaLastDate", "no key", NA, ""),
    ("1", "REFER_BENEFICIARY", "referBeneficiary", "administrativeArea", "Rigan Ori (prefilled)",
     "h_f_referral", "locality_code; additional_fields.localityCode, administrativeArea",
     "ADMIN_NI_01_01_06_02_13_RIGAN_ORI; same; Rigan Ori", CAP, ""),
    ("1", "REFER_BENEFICIARY", "referBeneficiary", "referredBy", "community distributor (prefilled)",
     "h_f_referral", "additional_fields.referredBy", "the CDD's user UUID", CAP, "Stored as the user's UUID, not the label"),
    ("1", "REFER_BENEFICIARY", "referBeneficiary", "healthFacility", "Fangwani health clinic",
     "h_f_referral", "project_facility_id", "PF-2026-06-10-068438", CAP, ""),
    # ---- Case 5: consent No (household only) -----------------------------------------------
    ("5", "HOUSEHOLD", "beneficiaryLocation", "administrativeArea", "Rigan Ori",
     "household; address", "additional_fields.administrativeArea; locality_boundary_code",
     "Rigan Ori; ADMIN_NI_01_01_06_02_13_RIGAN_ORI", CAP, ""),
    ("5", "HOUSEHOLD", "beneficiaryLocation", "latLng", "GPS fix (emulator)",
     "household; address", "latitude, longitude; location_accuracy", "10.5221983, 7.4387983; 5.0", CAP, ""),
    ("5", "HOUSEHOLD", "beneficiaryLocation", "typeOfAddress", "(hidden; default PERMANENT)",
     "household; address", "additional_fields.typeOfAddress; type", "PERMANENT; 0", CAP, "Default value"),
    ("5", "HOUSEHOLD", "caregiverConsent", "consentToParticipate", "No",
     "household", "additional_fields.caregiverConsent", "FALSE", CAP, ""),
    ("5", "HOUSEHOLD", "caregiverConsent", "negativeConsentReason", "QA test - consent refused",
     "household", "additional_fields.negativeConsentReason", "QA test - consent refused", CAP, "Shown only for consent No"),
    # ---- Case 6: Unable to Deliver (task, no task_resource) --------------------------------
    ("6", "UNABLETODELIVER", "unableToDeliver", "reason", "Beneficiary absent",
     "task", "status", "BENEFICIARY_ABSENT", CAP,
     "Stored only as the task status - no reason key in additional_fields. The screen marks the reason * (required)"),
    ("6", "UNABLETODELIVER", "unableToDeliver", "latLng", "Auto: 5.00 meters (emulator fix)",
     "address (related to the task)", "latitude, longitude, location_accuracy", "10.5221983, 7.4387983, 5.0", CAP, ""),
    ("6", "UNABLETODELIVER", "unableToDeliver", "comment", "QA test - absent",
     "task", "additional_fields.comment", "QA test - absent", CAP, ""),
    # ---- Case 8: revisit household 1, edit the head ---------------------------------------
    ("8", "HOUSEHOLD", "beneficiaryDetails", "phone", "10-digit test number from the user (ending 3803), through Edit Individual",
     "individual", "mobile_number", "the number entered (ending 3803)", CAP,
     "Exactly 10 digits: the 11-digit number first given shows 'Mobile number should be 10 digits.'"),
    # ---- Case 9: checklist with SMC Yes + date changed to No, then delivery --------------------
    ("9", "CHECKLIST", "eligibilityChecklist", "ec1", "No", "task", "additional_fields.ec1Value", "NO", CAP, ""),
    ("9", "CHECKLIST", "eligibilityChecklist", "ec2", "No", "task", "additional_fields.ec2Value", "NO", CAP, ""),
    ("9", "CHECKLIST", "eligibilityChecklist", "ec3", "No", "task", "additional_fields.ec3Value", "NO", CAP, ""),
    ("9", "CHECKLIST", "eligibilityChecklist", "ec4", "No", "task", "additional_fields.ec4Value", "NO", CAP, ""),
    ("9", "CHECKLIST", "eligibilityChecklist", "ec5", "No", "task", "additional_fields.ec5Value", "NO", CAP, ""),
    ("9", "CHECKLIST", "eligibilityChecklist", "malariaVaccine", "No", "task", "additional_fields.malariaVaccineReceived", "NO", CAP, ""),
    ("9", "CHECKLIST", "eligibilityChecklist", "smc", "Yes, then changed to No", "task", "additional_fields.smcReceived", "NO", CAP,
     "The last answer is stored"),
    ("9", "CHECKLIST", "eligibilityChecklist", "smcDate", "05 Nov 2026 picked, then hidden by SMC No", "task",
     "additional_fields.smcLastDate", "no key", AS, "The date picked before the change is dropped - correct"),
    ("9", "CHECKLIST", "eligibilityChecklist", "polio", "No", "task", "additional_fields.polioReceived", "NO", CAP, ""),
    ("9", "CHECKLIST", "eligibilityChecklist", "measlesRubella", "No", "task", "additional_fields.measlesRubellaReceived", "NO", CAP, ""),
    ("9", "DELIVERY", "DeliveryDetails", "dateOfRegistration", "11 Nov 2026 (read-only, today)",
     "task", "additional_fields.administrationStartTime, administrationEndTime, dateOfRegistration",
     "11 Nov 2026 10:32 / 10:35 IST; \"2026-11-11 10:32:08.958052\"", CAP, ""),
    ("9", "DELIVERY", "DeliveryDetails", "resourceCard", "Product: AZM", "task_resource", "product_variant_id", "PVAR-2025-01-03-000003", CAP, ""),
    ("9", "DELIVERY", "DeliveryDetails", "resourceCard", "Quantity Distributed: 8 (prefilled)", "task_resource", "quantity", "\"8\"", CAP, ""),
    ("9", "DELIVERY", "DeliveryDetails", "deliveryComment", "Delivery Successful",
     "task", "additional_fields.deliveryComment", "SUCCESSFUL_DELIVERY", CAP, ""),
    ("9", "DELIVERY", "DeliveryDetails", "deliveryComment", "Delivery Successful",
     "task_resource", "delivery_comment", "null", NOT, "Same as Case 2 - the column stays empty"),
    # ---- Case 7: redose of the Case 9 child, 5 minutes after its delivery ---------------------
    ("7", "REDOSE", "RedoseDetails", "dateOfRedose", "11 Nov 2026 (prefilled)",
     "task", "additional_fields.dateOfRedose", "\"2026-11-11 10:40:15.079749\"", CAP,
     "Text with microseconds; the time the form opened (submitted 10:41:51)"),
    ("7", "REDOSE", "RedoseDetails", "resourceCard", "AZM, Quantity Distributed 8 (prefilled)",
     "task_resource", "product_variant_id; quantity; is_delivered", "PVAR-2025-01-03-000003; \"8\"; 1", CAP, ""),
    ("7", "REDOSE", "RedoseDetails", "reasonForRedose", "Others", "task", "additional_fields.reasonForRedose", "OTHERS", CAP, ""),
    ("7", "REDOSE", "RedoseDetails", "redoseComments", "QA test", "task", "additional_fields.redoseComments", "QA test", CAP,
     "Shown for reason Others. \"QA test - redose\" was typed; only \"QA test\" reached the field (typing, not the app)"),
    # ---- Case 2: checklist -> delivery (stored in task / task_resource) --------------------
    ("2", "CHECKLIST", "eligibilityChecklist", "ec1", "No", "task", "additional_fields.ec1Value", "NO", CAP, ""),
    ("2", "CHECKLIST", "eligibilityChecklist", "ec2", "No", "task", "additional_fields.ec2Value", "NO", CAP, ""),
    ("2", "CHECKLIST", "eligibilityChecklist", "ec3", "No", "task", "additional_fields.ec3Value", "NO", CAP, ""),
    ("2", "CHECKLIST", "eligibilityChecklist", "ec4", "No", "task", "additional_fields.ec4Value", "NO", CAP, ""),
    ("2", "CHECKLIST", "eligibilityChecklist", "ec5", "No", "task", "additional_fields.ec5Value", "NO", CAP, ""),
    ("2", "CHECKLIST", "eligibilityChecklist", "malariaVaccine", "No", "task", "additional_fields.malariaVaccineReceived", "NO", CAP, ""),
    ("2", "CHECKLIST", "eligibilityChecklist", "malariaVaccineDate", "(not shown: No)", "task", "additional_fields.malariaVaccineLastDate", "no key", NA, ""),
    ("2", "CHECKLIST", "eligibilityChecklist", "smc", "Yes", "task", "additional_fields.smcReceived", "YES", CAP, ""),
    ("2", "CHECKLIST", "eligibilityChecklist", "smcDate", "06 Nov 2026", "task",
     "additional_fields.smcLastDate", "1793903400000 = 06 Nov 2026 00:00 IST", CAP, "Epoch milliseconds"),
    ("2", "CHECKLIST", "eligibilityChecklist", "polio", "Yes", "task", "additional_fields.polioReceived", "YES", CAP, ""),
    ("2", "CHECKLIST", "eligibilityChecklist", "polioDate", "03 Nov 2026", "task",
     "additional_fields.polioLastDate", "1793644200000 = 03 Nov 2026 00:00 IST", CAP, "Epoch milliseconds"),
    ("2", "CHECKLIST", "eligibilityChecklist", "measlesRubella", "No", "task", "additional_fields.measlesRubellaReceived", "NO", CAP, ""),
    ("2", "CHECKLIST", "eligibilityChecklist", "measlesRubellaDate", "(not shown: No)", "task", "additional_fields.measlesRubellaLastDate", "no key", NA, ""),
    ("2", "DELIVERY", "DeliveryDetails", "dateOfRegistration", "10 Nov 2026 (read-only, today)",
     "task", "additional_fields.administrationStartTime, administrationEndTime",
     "10 Nov 2026 16:25 / 16:27 IST", CAP, "Stored as start and end times"),
    ("2", "DELIVERY", "DeliveryDetails", "resourceCard", "Product: AZM",
     "task_resource", "product_variant_id", "PVAR-2025-01-03-000003", CAP, ""),
    ("2", "DELIVERY", "DeliveryDetails", "resourceCard", "Quantity Distributed: 8 (prefilled)",
     "task_resource", "quantity", "\"8\"", CAP, "Stored as text"),
    ("2", "DELIVERY", "DeliveryDetails", "deliveryComment", "Delivery Successful",
     "task", "additional_fields.deliveryComment", "SUCCESSFUL_DELIVERY", CAP, ""),
    ("2", "DELIVERY", "DeliveryDetails", "deliveryComment", "Delivery Successful",
     "task_resource", "delivery_comment", "null", NOT, "The comment is only in task.additional_fields - the column stays empty"),
    ("2", "DELIVERY", "DeliveryDetails", "scanner", "(hidden)", "-", "-", "-", NA, "Hidden on this form"),
    ("2", "DELIVERY", "DeliveryDetails", "latLng", "(hidden)", "task", "-", "not checked", NA, "Hidden on this form"),
    # ---- Case 3: checklist -> ineligible (stored in task, other keys) ----------------------
    ("3", "CHECKLIST", "eligibilityChecklist", "ec1", "No", "task", "additional_fields.ec1", "NO", CAP, "Key ec1 (not ec1Value)"),
    ("3", "CHECKLIST", "eligibilityChecklist", "ec2", "No", "task", "additional_fields.ec2", "NO", CAP, ""),
    ("3", "CHECKLIST", "eligibilityChecklist", "ec3", "No", "task", "additional_fields.ec3", "NO", CAP, ""),
    ("3", "CHECKLIST", "eligibilityChecklist", "ec4", "No", "task", "additional_fields.ec4", "NO", CAP, ""),
    ("3", "CHECKLIST", "eligibilityChecklist", "ec5", "Yes", "task", "additional_fields.ec5", "YES", CAP,
     "Makes the child ineligible: task.status = INELIGIBLE, no task_resource"),
    ("3", "CHECKLIST", "eligibilityChecklist", "malariaVaccine", "Yes", "task", "additional_fields.malariaVaccine", "YES", CAP,
     "Key malariaVaccine (not malariaVaccineReceived)"),
    ("3", "CHECKLIST", "eligibilityChecklist", "malariaVaccineDate", "04 Nov 2026", "task",
     "additional_fields.malariaVaccineDate", "\"2026-11-04 00:00:00.000\"", CAP, "Text date - delivery and referral store epoch milliseconds"),
    ("3", "CHECKLIST", "eligibilityChecklist", "smc", "No", "task", "additional_fields.smc", "NO", CAP, ""),
    ("3", "CHECKLIST", "eligibilityChecklist", "smcDate", "(not shown: No)", "task", "additional_fields.smcDate", "no key", NA, ""),
    ("3", "CHECKLIST", "eligibilityChecklist", "polio", "No", "task", "additional_fields.polio", "NO", CAP, ""),
    ("3", "CHECKLIST", "eligibilityChecklist", "polioDate", "(not shown: No)", "task", "additional_fields.polioDate", "no key", NA, ""),
    ("3", "CHECKLIST", "eligibilityChecklist", "measlesRubella", "No", "task", "additional_fields.measlesRubella", "NO", CAP, ""),
    ("3", "CHECKLIST", "eligibilityChecklist", "measlesRubellaDate", "(not shown: No)", "task", "additional_fields.measlesRubellaDate", "no key", NA, ""),
    # ---- Case 4: checklist -> referral with Case 2's dates ---------------------------------
    ("4", "CHECKLIST", "eligibilityChecklist", "ec1", "Yes", "h_f_referral", "additional_fields.ec1Value", "YES", CAP, "Triggers the referral"),
    ("4", "CHECKLIST", "eligibilityChecklist", "ec2", "No", "h_f_referral", "additional_fields.ec2Value", "NO", CAP, ""),
    ("4", "CHECKLIST", "eligibilityChecklist", "ec3", "No", "h_f_referral", "additional_fields.ec3Value", "NO", CAP, ""),
    ("4", "CHECKLIST", "eligibilityChecklist", "ec4", "No", "h_f_referral", "additional_fields.ec4Value", "NO", CAP, ""),
    ("4", "CHECKLIST", "eligibilityChecklist", "ec5", "No", "h_f_referral", "additional_fields.ec5Value", "NO", CAP, ""),
    ("4", "CHECKLIST", "eligibilityChecklist", "malariaVaccine", "No", "h_f_referral", "additional_fields.malariaVaccineReceived", "NO", CAP, ""),
    ("4", "CHECKLIST", "eligibilityChecklist", "malariaVaccineDate", "(not shown: No)", "h_f_referral", "additional_fields.malariaVaccineLastDate", "no key", NA, ""),
    ("4", "CHECKLIST", "eligibilityChecklist", "smc", "Yes", "h_f_referral", "additional_fields.smcReceived", "YES", CAP, ""),
    ("4", "CHECKLIST", "eligibilityChecklist", "smcDate", "06 Nov 2026 (as Case 2)", "h_f_referral",
     "additional_fields.smcLastDate", "1793903400000 = 06 Nov 2026 00:00 IST", CAP, "Identical to Case 2's delivery"),
    ("4", "CHECKLIST", "eligibilityChecklist", "polio", "Yes", "h_f_referral", "additional_fields.polioReceived", "YES", CAP, ""),
    ("4", "CHECKLIST", "eligibilityChecklist", "polioDate", "03 Nov 2026 (as Case 2)", "h_f_referral",
     "additional_fields.polioLastDate", "1793644200000 = 03 Nov 2026 00:00 IST", CAP, "Identical to Case 2's delivery"),
    ("4", "CHECKLIST", "eligibilityChecklist", "measlesRubella", "No", "h_f_referral", "additional_fields.measlesRubellaReceived", "NO", CAP, ""),
    ("4", "CHECKLIST", "eligibilityChecklist", "measlesRubellaDate", "(not shown: No)", "h_f_referral", "additional_fields.measlesRubellaLastDate", "no key", NA, ""),
    ("4", "REFER_BENEFICIARY", "referBeneficiary", "healthFacility", "Fangwani health clinic",
     "h_f_referral", "project_facility_id", "PF-2026-06-10-068438", CAP, ""),
    ("4", "REFER_BENEFICIARY", "referBeneficiary", "administrativeArea", "Rigan Ori (prefilled)",
     "h_f_referral", "additional_fields.localityCode, administrativeArea", "ADMIN_NI_01_01_06_02_13_RIGAN_ORI; Rigan Ori", CAP, ""),
    ("4", "REFER_BENEFICIARY", "referBeneficiary", "referredBy", "community distributor (prefilled)",
     "h_f_referral", "additional_fields.referredBy", "the CDD's user UUID", CAP, ""),
]

# Values the app sets on the record itself (no form field), read in the same
# queries, and the planned checks of Cases 8-10 that are not a single field.
# (case, flow, page, field id, label, entered, table, column / key, stored, status, notes)
APP = "(set by the app)"
EXTRA = [
    (1, "ADD_MEMBER", "beneficiaryDetails", "(membership)", "Child linked to the household", APP,
     "household_member; project_beneficiary", "is_head_of_household, household; date_of_registration",
     "0, same household as the head; 1794301532005 = 10 Nov 2026 14:35 IST", CAP, ""),
    (1, "REFER_BENEFICIARY", "referBeneficiary", "(referral record)", "Child on the referral", APP,
     "h_f_referral", "name; beneficiary_id; referral_code", "QAID-DB1-C1 Test; 152320332491; the child's client reference", CAP, ""),
    (1, "REFER_BENEFICIARY", "referBeneficiary", "(child and household)", "Copied from the household and child", APP,
     "h_f_referral", "additional_fields.nameOfReferral, nameOfHouseholdHead, gender, ageInMonths, latitude, longitude",
     "QAID-DB1-C1 Test; QAID-DB1-H Test; FEMALE; 24; 10.5221983; 7.4387983", CAP, ""),
    (1, "REFER_BENEFICIARY", "referBeneficiary", "(referral reason)", "Referral reason", APP,
     "h_f_referral", "symptom; additional_fields.referralReasons, referralSymptom", "SICK; SICK; SICK", CAP,
     "The referral came from ec1 = Yes (allergy to azithromycin) - is SICK intended? See Findings"),
    (1, "REFER_BENEFICIARY", "referBeneficiary", "(evaluation)", "Date of evaluation, cycle, flow", APP,
     "h_f_referral", "additional_fields.dateOfEvaluation, referralCycle, cycleIndexStamp, flow",
     "1794304768794 = 10 Nov 2026 15:29 IST; 2; 2; smcDone", CAP, ""),
    (2, "DELIVERY", "DeliveryDetails", "(delivered)", "Delivery status", APP,
     "task; task_resource", "status; is_delivered", "ADMINISTRATION_SUCCESS; 1", CAP, ""),
    (2, "DELIVERY", "DeliveryDetails", "(child and household)", "Copied from the household and child", APP,
     "task", "additional_fields.beneficiaryId, childName, ageInMonths, gender, height, headName, memberCount",
     "152113181641; QAID-DB2-C1 Test; 24; FEMALE; \"85\"; QAID-DB2-H Test; 5", CAP, ""),
    (2, "DELIVERY", "DeliveryDetails", "(references)", "Links to the household and child", APP,
     "task", "additional_fields.householdClientReferenceId, individualClientReferenceId",
     "the household's and the child's client references", CAP, ""),
    (2, "DELIVERY", "DeliveryDetails", "(dose)", "Dose, cycle, strategy, flow", APP,
     "task", "additional_fields.doseIndex, cycleIndex, deliveryStrategy, flow", "1; 2; DIRECT; smcDone", CAP, ""),
    (2, "DELIVERY", "DeliveryDetails", "(registration date)", "Date of registration on the task", APP,
     "task", "additional_fields.dateOfRegistration", "\"2026-11-10 16:25:46.421183\"", CAP,
     "Text with microseconds - the other dates are epoch milliseconds"),
    (3, "CHECKLIST", "eligibilityChecklist", "(outcome)", "Ineligible", APP,
     "task; task_resource", "status; rows", "INELIGIBLE; 0 rows", CAP, "The child's card reads Ineligible"),
    (3, "CHECKLIST", "eligibilityChecklist", "(child and household)", "Copied from the household and child", APP,
     "task", "additional_fields.beneficiaryId, childName, ageInMonths, gender, headName, memberCount",
     "152132223152; QAID-DB3-C1 Test; 24; FEMALE; QAID-DB3-H Test; 5", CAP, "No height key (the delivery task has one)"),
    (3, "CHECKLIST", "eligibilityChecklist", "(references)", "Links to the household and child", APP,
     "task", "additional_fields.householdClientReferenceId, individualClientReferenceId",
     "the household's and the child's client references", CAP, ""),
    (3, "CHECKLIST", "eligibilityChecklist", "(flow)", "Flow, cycle", APP,
     "task", "additional_fields.flow, cycleIndexStamp", "smcDone; 2", CAP, ""),
    (4, "REFER_BENEFICIARY", "referBeneficiary", "(referral record)", "Child on the referral", APP,
     "h_f_referral", "name; beneficiary_id", "QAID-DB4-C1 Test; 152229141615", CAP, ""),
    (4, "REFER_BENEFICIARY", "referBeneficiary", "(child and household)", "Copied from the household and child", APP,
     "h_f_referral", "additional_fields.nameOfReferral, nameOfHouseholdHead, gender, ageInMonths, latitude, longitude",
     "QAID-DB4-C1 Test; QAID-DB4-H Test; FEMALE; 24; 10.5221983; 7.4387983", CAP, ""),
    (4, "REFER_BENEFICIARY", "referBeneficiary", "(referral reason)", "Referral reason", APP,
     "h_f_referral", "symptom; additional_fields.referralReasons, referralSymptom", "SICK; SICK; SICK", CAP,
     "Again SICK for an ec1 = Yes referral"),
    (4, "REFER_BENEFICIARY", "referBeneficiary", "(evaluation)", "Date of evaluation, cycle, flow", APP,
     "h_f_referral", "additional_fields.dateOfEvaluation, referralCycle, cycleIndexStamp, flow",
     "1794309880033 = 10 Nov 2026 16:54 IST; 2; 2; smcDone", CAP, ""),
    (5, "HOUSEHOLD", "caregiverConsent", "(outcome)", "Registration stops at the household", APP,
     "household_member; individual; name; project_beneficiary", "rows for this household / name QAID-DB5-H",
     "0; 0; 0; 0", AS, "No person is registered without consent. The name typed in search is not stored"),
    (5, "HOUSEHOLD", "caregiverConsent", "(member count)", "Member count and head flag on the household", APP,
     "household", "member_count; additional_fields.memberCount, isHeadOfFamily, cycleIndexStamp",
     "1; \"1\", \"true\", 2", CAP, "Check: set although nobody is registered - see Findings"),
    (6, "UNABLETODELIVER", "unableToDeliver", "(outcome)", "Not delivered", APP,
     "task; task_resource", "rows; actual_start_date, actual_end_date; client_created_time",
     "1 task, 0 task_resource; null, null; 1794371958591 = 11 Nov 2026 10:09 IST", CAP,
     "The card reads Beneficiary Absent; Dose and Unable To Deliver are gone"),
    (6, "UNABLETODELIVER", "unableToDeliver", "(child and household)", "Copied from the household and child", APP,
     "task", "additional_fields.beneficiaryId, childName, ageInMonths, gender, headName, memberCount, cycleIndex, flow",
     "158181318102; QAID-DB6-C1 Test; 24; FEMALE; QAID-DB6-H Test; 5; 2; smcDone", CAP, ""),
    # Planned checks (cases not run yet)
    (8, "HOUSEHOLD", "beneficiaryDetails", "(reopen)", "Saved values shown again", "Reopen HH1 -> Edit Individual (head)",
     "household; individual; name; household_member", "values on screen",
     "Overview: QAID-DB1-H Test, Rigan Ori, 5 members, consent True, FEMALE 30y. Edit form: QAID-DB1-H / Test, 10 Nov 1996, 30 y 0 m, Female, mobile empty",
     CAP, "Every saved value comes back. The head's edit form is titled Child's Details"),
    (8, "HOUSEHOLD", "beneficiaryDetails", "(same row)", "The edit updates the existing row", APP,
     "individual; name; identifier", "client_reference_id; rows",
     "unchanged (9bc9ef40...); 1 individual, 1 name, 1 identifier 152062311161; total individuals unchanged (363)", CAP,
     "No duplicate person; the success screen shows the same Token ID"),
    (8, "HOUSEHOLD", "beneficiaryDetails", "(change tracking)", "Change time and version", APP,
     "individual", "client_modified_time; audit_modified_time; row_version",
     "10 Nov 14:33 -> 11 Nov 11:43 IST; still 10 Nov 14:33; null before and after", CAP,
     "Check: row_version stays null and audit_modified_time is not updated - see Findings"),
    (8, "HOUSEHOLD", "beneficiaryDetails", "(new key)", "identifiers in additional_fields", APP,
     "individual", "additional_fields.identifiers", "\"UNIQUE_BENEFICIARY_ID,152062311161\" (added by the edit)", CAP,
     "Not there before the edit; household_member row untouched"),
    (9, "DELIVERY", "DeliveryDetails", "(delivered)", "Delivery status", APP,
     "task; task_resource", "status; is_delivered", "ADMINISTRATION_SUCCESS; 1", CAP, ""),
    (9, "DELIVERY", "DeliveryDetails", "(child and household)", "Copied from the household and child", APP,
     "task", "additional_fields.beneficiaryId, childName, ageInMonths, gender, height, headName, memberCount, doseIndex, cycleIndex, deliveryStrategy",
     "158221616161; QAID-DB9-C1 Test; 24; FEMALE; \"85\"; QAID-DB9-H Test; 5; 1; 2; DIRECT", CAP, ""),
    (7, "REDOSE", "RedoseDetails", "(outcome)", "Redose record", APP,
     "task; task_resource", "a new task row: status, additional_fields.taskType; task_resource.delivery_comment",
     "VISITED, REDOSE; \"REDOSE\". Case 9's delivery task is unchanged", CAP,
     "Check: status VISITED for a redose that was given - see Findings. The card then reads Redose Completed and Redose is greyed out"),
    (7, "REDOSE", "RedoseDetails", "(child and household)", "Copied from the household and child", APP,
     "task", "additional_fields.beneficiaryId, childName, ageInMonths, gender, height, headName, memberCount, cycleIndex, flow",
     "158221616161; QAID-DB9-C1 Test; 24; FEMALE; \"85\"; QAID-DB9-H Test; 5; 2; smcDone", CAP, ""),
    (10, "CHECKLIST", "eligibilityChecklist", "(abandoned)", "Checklist left before referral or delivery",
     "ec1 No, ec2 No, then the app's Back",
     "task; h_f_referral; referral; service", "rows for that child (service: all rows)",
     "0; 0; 0; 0 - the child keeps its project_beneficiary row only", AS,
     "Back gave no 'discard changes?' warning; the card still reads Not Administered with Dose"),
]

# Shown fields no case has used yet - the Not tested rows, with the planned
# case (RESULTS.md, "Not run yet") and the table they are expected in.
NOT_TESTED = {
}

FINDINGS = [
    ("Delivery (Case 2)", "Not captured", "task_resource.delivery_comment is null although Delivery Comments = Delivery Successful was chosen; the value is only in task.additional_fields.deliveryComment.",
     "Is the task_resource.delivery_comment column meant to be filled?"),
    ("Checklist storage (Cases 1-4)", "Inconsistent", "The same checklist answers are stored under different keys and formats: delivery and referral use ec1Value..ec5Value, malariaVaccineReceived / smcReceived / polioReceived / measlesRubellaReceived and *LastDate as epoch milliseconds; the ineligible task uses ec1..ec5, malariaVaccine / smc / polio / measlesRubella and malariaVaccineDate as text \"yyyy-MM-dd HH:mm:ss.SSS\", and stores no height.",
     "Should every path store one set of keys and one date format?"),
    ("Referral reason (Cases 1, 4)", "Check", "Every checklist referral is stored with symptom / referralReasons / referralSymptom = SICK, although both referrals here came from ec1 = Yes (allergy to azithromycin).",
     "Is SICK intended for every checklist referral?"),
    ("Referral table (Cases 1, 4)", "Info", "The CDD's referral is stored in h_f_referral; the referral table stays empty (0 rows) and no task row is made.", ""),
    ("SMC date key (Cases 1, 2, 4)", "Info", "The SMC date is stored as smcLastDate (epoch milliseconds, local midnight) in additional_fields, not as smc_date.", ""),
    ("Checklist Submit", "Info", "The checklist's Submit saves nothing by itself (the live config only navigates); its answers are stored with the referral, delivery or ineligible record. Confirmed by Case 10: an abandoned checklist leaves no record.", ""),
    ("Flow (Cases 1-4)", "Info", "flow = smcDone is stored on every referral and task.", ""),
    ("Unable to Deliver (Case 6)", "Info", "The reason is kept only as task.status (BENEFICIARY_ABSENT); there is no reason key, and actual_start_date / actual_end_date are null - the time is only in client_created_time. Unable To Deliver is offered on the card before any checklist.",
     "Is the status enough for reports that need the reason?"),
    ("Redose window (Case 7)", "Info", "Redose is disabled once isRedoseWindowExpired(task) is true (form config); on 11 Nov the Redose button of Case 2's child (delivered 10 Nov 16:27) was greyed out. The window length is in the app code, so redose is tested straight after a new delivery.", ""),
    ("Redose (Case 7)", "Check", "A redose is stored as a new task with status VISITED (taskType REDOSE), not ADMINISTRATION_SUCCESS; its task_resource has delivery_comment \"REDOSE\" while a normal delivery leaves that column null. dateOfRedose is the time the form opened, as text with microseconds.",
     "Is VISITED the intended status for a given redose?"),
    ("Edit (Case 8)", "Check", "Editing the head updates the same individual row and stores the mobile number, but row_version stays null and audit_modified_time keeps the registration time; only client_modified_time moves. The edit also adds an identifiers key to individual.additional_fields. The head's edit form is titled Child's Details.",
     "Are row_version and audit_modified_time meant to change on a local edit? Should the head's form say Child's Details?"),
    ("Mobile number (Case 8)", "Info", "The mobile number must be exactly 10 digits (no leading 0 or +234); 11 digits show 'Mobile number should be 10 digits.'", ""),
    ("Answer change (Case 9)", "Info", "Changing SMC from Yes (with a date) to No drops the date: smcReceived NO and no smcLastDate key. Correct.", ""),
    ("Abandoned checklist (Case 10)", "Info", "Leaving a partly answered checklist with Back saves nothing (no task, h_f_referral, referral or service row) and gives no warning.", ""),
    ("Consent No (Case 5)", "Check", "The refused household is saved with member_count 1, memberCount \"1\" and isHeadOfFamily \"true\", although no member, individual or project_beneficiary row is made.",
     "Should a consent-No household store member_count 0 and no isHeadOfFamily?"),
    ("Dates", "Info", "Formats differ across one record: individual.date_of_birth dd/MM/yyyy; project_beneficiary.date_of_registration epoch ms; task dateOfRegistration text with microseconds; checklist dates epoch ms or text (see above).", ""),
    ("Registration (Cases 2-4)", "Info", "Only Case 1's registration rows were read from the DB; Cases 2-4 used the same form and were checked for the checklist and its outcome only.", ""),
]


def field_meta():
    cfg = next(c for c in json.load(open(os.path.join(ROOT, "config", "formconfig-kaduna-20261102.json"), encoding="utf-8"))
               if c["name"] == "REGISTRATION")
    loc = json.load(open(os.path.join(ROOT, "config", "localization-en.json"), encoding="utf-8"))
    meta, order = {}, []
    for flow, page, screen in SCREENS:
        fl = next(f for f in cfg["flows"] if f["name"] == flow)
        pg = next(p for p in fl["pages"] if p["page"] == page)
        for i, f in enumerate((pg.get("properties") or []) + (pg.get("body") or [])):
            if f.get("format") in ("heading",) or f.get("type") == "template":
                continue
            fn = f.get("fieldName")
            vc = f.get("visibilityCondition") or {}
            exprs = [e.get("condition", "") for e in vc.get("expression", [])] if isinstance(vc.get("expression"), list) else []
            parent = " ".join(" ".join(exprs).split()).replace("&& ", "&& ")
            label = loc.get(f.get("label"), f.get("label") or "")
            meta[(flow, page, fn)] = {
                "screen": screen, "label": label, "type": f"{f.get('type', '')}/{f.get('format', '')}",
                "mandatory": "Yes" if f.get("mandatory") or f.get("required") else "No",
                "conditional": "Yes" if exprs else ("Hidden" if f.get("hidden") else "No"),
                "parent": parent, "order": (SCREENS.index((flow, page, screen)), i),
            }
            order.append((flow, page, fn))
    return meta, order


def main():
    meta, order = field_meta()
    rows = []
    used = set()
    for case, flow, page, fn, entered, table, col, stored, status, notes in OBS:
        m = meta[(flow, page, fn)]
        used.add((flow, page, fn))
        rows.append([int(case), "REGISTRATION", flow, m["screen"], fn, m["label"], m["type"], m["mandatory"], m["conditional"],
                     m["parent"], entered, table, col, stored, status, notes, m["order"]])
    for i, (case, flow, page, fn, label, entered, table, col, stored, status, notes) in enumerate(EXTRA):
        m = meta.get((flow, page, fn))
        if m:  # a form field checked again (Case 9)
            rows.append([case, "REGISTRATION", flow, m["screen"], fn, m["label"], m["type"], m["mandatory"], m["conditional"],
                         m["parent"], entered, table, col, stored, status, notes, m["order"]])
            continue
        s = next(j for j, sc in enumerate(SCREENS) if sc[:2] == (flow, page))
        kind = "set by the app" if status != NT else "check"
        rows.append([case, "REGISTRATION", flow, SCREENS[s][2], fn, label, kind, "-", "-", "-", entered,
                     table, col, stored, status, notes, (s, 100 + i)])
    for key, (case, table, col, why) in NOT_TESTED.items():
        m = meta[key]
        rows.append([case, "REGISTRATION", key[0], m["screen"], key[2], m["label"], m["type"], m["mandatory"], m["conditional"],
                     m["parent"], "-", table, col, "-", NT, why, m["order"]])
    missing = [k for k in order if k not in used and k not in NOT_TESTED]
    if missing:
        raise SystemExit(f"Fields with no row: {missing}")
    rows.sort(key=lambda r: (r[0], r[16]))

    headers = ["Case", "Module", "Flow", "Screen", "Field ID", "Field label", "Field type", "Mandatory", "Conditional",
               "Parent field / condition", "Value entered", "Table", "Column / key", "Value stored in DB", "Status", "Notes"]
    widths = [6, 16, 18, 26, 20, 40, 16, 11, 12, 34, 28, 22, 36, 38, 15, 44]

    font = Font(name="Arial", size=10)
    bold = Font(name="Arial", size=10, bold=True)
    head_fill = PatternFill("solid", fgColor="1F3864")
    head_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    fills = {CAP: "E2EFDA", NOT: "F8CBAD", AS: "DDEBF7", NA: "EDEDED", NT: "FFF2CC"}
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap = Alignment(wrap_text=True, vertical="top")

    wb = Workbook()

    def table_sheet(ws, data):
        ws.append(headers)
        for c in ws[1]:
            c.font, c.fill, c.alignment, c.border = head_font, head_fill, Alignment(wrap_text=True, vertical="center"), border
        for r in data:
            ws.append(r[:16])
            for c in ws[ws.max_row]:
                c.font, c.alignment, c.border = font, wrap, border
            ws.cell(ws.max_row, 15).fill = PatternFill("solid", fgColor=fills[r[14]])
            ws.cell(ws.max_row, 15).font = bold
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "F2"
        ws.auto_filter.ref = f"A1:P{ws.max_row}"

    # ---- Summary -----------------------------------------------------------------------
    ws = wb.active
    ws.title = "Summary"
    ws["A1"] = "CDD actions - fields captured / not captured in the local DB"
    ws["A1"].font = Font(name="Arial", size=14, bold=True)
    info = [
        ("App", "Kaduna AZM org.egov.azm.gombe 2.2.122 (-db build), emulator-5554, CDD dis-qa-oct29, Fangwani Health Clinic / Rigan Ori"),
        ("Checked", "2026-11-10, one record per case; each record read from the app's own local DB through its DB card (Drift viewer, SQL)"),
        ("Source", "db-audit/RESULTS.md; SQL and answers in artifacts/db-audit/queries/; field list from the live form config (REGISTRATION v8)"),
    ]
    for i, (k, v) in enumerate(info, 3):
        ws.cell(i, 1, k).font = bold
        ws.cell(i, 2, v).font = font
    ws["A7"] = "Status"
    ws["B7"] = "Meaning"
    for c in (ws["A7"], ws["B7"]):
        c.font, c.fill = head_font, head_fill
    legend = [
        (CAP, "The value entered is in the DB (table / column / key shown)"),
        (NOT, "Entered, but not in the column expected for it"),
        (AS, "Nothing is stored, and nothing should be (e.g. no person without consent, no record for an abandoned checklist)"),
        (NA, "Not shown in that case (hidden field, or its condition not met), or optional and left blank"),
        (NT, "A field or check of a case not run yet (see the Cases sheet)"),
    ]
    for i, (s, m) in enumerate(legend, 8):
        ws.cell(i, 1, s).font = bold
        ws.cell(i, 1).fill = PatternFill("solid", fgColor=fills[s])
        ws.cell(i, 2, m).font = font

    ws["A13"] = "Case"
    for j, s in enumerate(STATUSES + ["Total"], 2):
        ws.cell(13, j, s)
    for c in ws[13][:len(STATUSES) + 2]:
        c.font, c.fill, c.alignment = head_font, head_fill, Alignment(wrap_text=True)
    case_keys = list(CASES)
    for i, k in enumerate(case_keys, 14):
        ws.cell(i, 1, CASES[k]).font = font
        ws.cell(i, 1).alignment = Alignment(wrap_text=True, vertical="top")
        for j, s in enumerate(STATUSES, 2):
            ws.cell(i, j, f"=COUNTIFS('All fields'!$A:$A,{k},'All fields'!$O:$O,\"{s}\")").font = font
        ws.cell(i, 2 + len(STATUSES), f"=SUM(B{i}:{get_column_letter(1 + len(STATUSES))}{i})").font = bold
    tot = 14 + len(case_keys)
    ws.cell(tot, 1, "Total").font = bold
    for j in range(2, 3 + len(STATUSES)):
        col = get_column_letter(j)
        ws.cell(tot, j, f"=SUM({col}14:{col}{tot - 1})").font = bold
    ws.cell(tot + 2, 1, "Findings for the dev team").font = bold
    ws.cell(tot + 2, 2, "=COUNTA(Findings!A:A)-1").font = bold
    ws.cell(tot + 2, 3, "see the Findings sheet").font = font
    ws.column_dimensions["A"].width = 70
    ws.column_dimensions["B"].width = 16
    for col in "CDEFG":
        ws.column_dimensions[col].width = 16
    ws.cell(3, 2).alignment = ws.cell(4, 2).alignment = ws.cell(5, 2).alignment = Alignment(wrap_text=False)

    # ---- Cases ---------------------------------------------------------------------------
    wc = wb.create_sheet("Cases")
    wc.append(["Case", "Status", "What was done in the app", "Household head (ID)", "Child (ID)",
               "When (2026, IST)", "Stored in", "Result / what to check", "Field rows",
               "Captured", "Not captured", "Not tested"])
    for c in wc[1]:
        c.font, c.fill, c.alignment, c.border = head_font, head_fill, Alignment(wrap_text=True, vertical="center"), border
    for info in CASE_INFO:
        r = wc.max_row + 1
        wc.append(list(info) + [
            f"=COUNTIFS('All fields'!$A:$A,A{r})",
            f"=COUNTIFS('All fields'!$A:$A,A{r},'All fields'!$O:$O,\"{CAP}\")",
            f"=COUNTIFS('All fields'!$A:$A,A{r},'All fields'!$O:$O,\"{NOT}\")",
            f"=COUNTIFS('All fields'!$A:$A,A{r},'All fields'!$O:$O,\"{NT}\")"])
        for c in wc[r]:
            c.font, c.alignment, c.border = font, wrap, border
        wc.cell(r, 2).font = bold
        wc.cell(r, 2).fill = PatternFill("solid", fgColor=fills[CAP] if info[1] == "Done" else fills[NT])
    for i, w in enumerate([6, 12, 44, 26, 28, 26, 40, 52, 10, 10, 10, 10], 1):
        wc.column_dimensions[get_column_letter(i)].width = w
    wc.freeze_panes = "C2"
    wc.auto_filter.ref = f"A1:L{wc.max_row}"

    # ---- Field sheets ---------------------------------------------------------------------
    table_sheet(wb.create_sheet("All fields"), rows)
    # One tab per status, so "Not captured" holds only the real gaps. Not
    # tested appears only while a planned case is still to run.
    for s in STATUSES:
        part = [r for r in rows if r[14] == s]
        if part or s in (CAP, NOT):
            table_sheet(wb.create_sheet(s), part)

    # ---- Findings -----------------------------------------------------------------------
    wf = wb.create_sheet("Findings")
    wf.append(["Area", "Type", "Finding", "Question for the dev"])
    for c in wf[1]:
        c.font, c.fill, c.border = head_font, head_fill, border
    for f in FINDINGS:
        wf.append(list(f))
        for c in wf[wf.max_row]:
            c.font, c.alignment, c.border = font, wrap, border
    for i, w in enumerate([28, 14, 90, 50], 1):
        wf.column_dimensions[get_column_letter(i)].width = w
    wf.freeze_panes = "A2"

    wb.save(OUT)
    recalc()
    print(OUT, len(rows), "rows;", {s: sum(1 for r in rows if r[14] == s) for s in STATUSES})


def recalc():
    """openpyxl saves formulas without values; a round trip through
    LibreOffice stores the computed counts, so previewers show them too."""
    import shutil
    import subprocess
    import tempfile
    soffice = shutil.which("soffice") or r"C:\Program Files\LibreOffice\program\soffice.exe"
    if not os.path.exists(soffice):
        print("LibreOffice not found - Summary counts are computed when Excel opens the file")
        return
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([soffice, "--headless", "--norestore", "--calc", "--convert-to",
                        "xlsx:Calc MS Excel 2007 XML", "--outdir", tmp, OUT], check=True, capture_output=True)
        shutil.copyfile(os.path.join(tmp, os.path.basename(OUT)), OUT)


if __name__ == "__main__":
    main()
