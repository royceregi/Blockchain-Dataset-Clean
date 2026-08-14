# Finalized dataset specification

This file defines the **four CSV datasets** that preprocessing must produce. They sit in `preprocessing/data/finalized/` and feed IR, NLP, blockchain, and security agents.

How to generate them: see [`preprocessing/README.md`](preprocessing/README.md).  
How they become a database: see [`property-database/table.md`](property-database/table.md).

## Data folders

Under `preprocessing/data/`:

| Folder | Meaning |
|--------|---------|
| `raw/` | Original files from DLD / other sources. Scripts never overwrite these. |
| `preprocessed/` | Intermediate extracts gathered by other agents (enriched owners, deeds, wallets). |
| `cleaned/` | Noise, duplicates, and invalid dates removed. This is what the **database ETL** loads. |
| `finalized/` | Wide CSVs with the **mandatory columns below**, ready for analysis or agents. |

Study period for DLD transactions: **2021-01-01** through **2023-12-31**.

## CSV naming vs this spec

Slash and parenthesis names in the original brief are flattened so they work as CSV headers:

| Spec wording | CSV column |
|--------------|------------|
| Owner_Name / Owner_ID | `Owner_Name` and `Owner_ID` |
| Owner_NIC / National_ID | `Owner_NIC` |
| Land_Extent / Area | `Land_Extent_Area` |
| Notary_ID / Notary_Name | `Notary_Name` |
| Transaction_ID (hash) | `Transaction_ID` |
| From_Wallet / To_Wallet | `From_Wallet` and `To_Wallet` |
| Name / Contact | `Name_Contact` |
| Auth_Credentials (hashed) | `Auth_Credentials_Hashed` |

---

## 1. Property / land title records

**File:** `preprocessing/data/finalized/property_land_title_records.csv`  
**Feeds:** IR + NLP agents (titles, deeds, owners, values).

| Column | Purpose |
|--------|---------|
| `Property_ID` | Unique property key (also used on-chain). Project-generated grouping ID, not a legal title number. |
| `Property_Name` | Descriptive name (e.g. project / building name). |
| `Property_Group_ID` | Groups sub-plots or multi-parcel developments. |
| `Group_Name` | Parent estate or development group. |
| `Title_Deed_Number` | Legal deed reference. |
| `Owner_Name` | Current owner name. |
| `Owner_ID` | Linked stakeholder ID (`USER…`). |
| `Owner_NIC` | **PII** — national ID. Hash or anonymize before sharing. |
| `Property_Address` | Physical address (area, building, project). |
| `Nearest_Landmark` | Nearby landmark. |
| `Land_Extent_Area` | Size (sq. m in this dataset). |
| `Procedural_Area_Type` | Zone / legal class (Residential, Commercial, …). |
| `Current_Usage_Type` | Active use. |
| `Previous_Usage_Type` | Use before the current registration. |
| `Current_Subtype` | Fine subtype (Villa, Apartment, …). |
| `Property_Subtype` | Master category (same source field as current subtype here). |
| `Land_Boundaries` | North / South / East / West markers in one string. |
| `Registration_Type` | Registry action (first registration, transfer, off-plan, …). |
| `Registration_Year` | Year of registration. |
| `Registration_Month` | Month (1–12). |
| `Registration_Quarter` | `Q1`–`Q4`. |
| `Registration_Date` | Day of month (1–31). |
| `Registration_Day` | Weekday name. |
| `Registration_Time` | Time (`HH:MM:SS`). |
| `Notary_Name` | Notary who officiated. |
| `Witness_Details` | Witness names (combined). |
| `Registration_Fees_Paid` | Registry / total fees. |
| `Stamp_Duty_Taxes_Paid` | Stamp duty / transfer tax portion. |
| `Current_Value` | Latest assessed value (AED). |
| `Previous_Value` | Previous valuation. |
| `Previous_Owners` | Prior owner name(s) for provenance. |
| `Legal_Status` | Clear, Disputed, Mortgaged, Under Litigation, … |
| `Encumbrances` | Mortgages, liens, caveats. |
| `Document_Text` | Unstructured deed text (NLP). |
| `Document_Hash` | Hash of the deed (tamper check). |
| `Verification_Status` | Verified, Pending, Rejected. |
| `Survey_Plan_Number` | Survey plan reference. |

---

## 2. Blockchain transaction ledger

**File:** `preprocessing/data/finalized/blockchain_transaction_ledger.csv`  
**Feeds:** blockchain / agent layer.  
**Link:** `Property_ID` matches Table 1.

Hashes, wallets, and contract addresses in this project are **prototype** fields (generated or enriched), not a live public chain.

| Column | Purpose |
|--------|---------|
| `Transaction_ID` | Cryptographic (or prototype) hash identifying the tx. |
| `Block_Number` | Sequential block containing the tx. |
| `Tx_Year` | Year the block was timestamped. |
| `Tx_Month` | Month (1–12). |
| `Tx_Quarter` | `Q1`–`Q4`. |
| `Tx_Date` | Day of month (1–31). |
| `Tx_Day` | Weekday name. |
| `Tx_Time` | Time (`HH:MM:SS`). |
| `Property_ID` | Foreign key to title records. |
| `From_Wallet` | Seller / grantor address. |
| `To_Wallet` | Buyer / grantee address. |
| `Transaction_Type` | Registration, Transfer, Mortgage, … |
| `Smart_Contract_Address` | Contract that processed the logic. |
| `Transaction_Status` | Pending, Confirmed, Failed. |
| `Digital_Signature` | Signature of origin. |
| `Consensus_Verification` | Validator confirmation text. |

---

## 3. Users / stakeholders

**File:** `preprocessing/data/finalized/users_stakeholders.csv`  
**Feeds:** security and authentication agent.

| Column | Purpose |
|--------|---------|
| `User_ID` | Primary key (`USER000001`, …). |
| `Role` | Buyer, Seller, Notary, Registrar, Surveyor, Agent, Admin, Investor, … |
| `Name_Contact` | **PII** — name plus email / phone / NIC where available. |
| `Wallet_Address` | Public wallet. |
| `Auth_Credentials_Hashed` | Password hash / MFA material (never plaintext). |
| `Associated_Property_IDs` | Properties linked to this user (comma-separated). |
| `Data_Access_Scope` | Permission scope (mirrors access level in this build). |
| `KYC_Status` | Verified, Unverified, Pending, Suspended. |
| `Access_Level` | RBAC level (Standard, Elevated, …). |

---

## 4. Query / interaction logs

**File:** `preprocessing/data/finalized/query_interaction_logs.csv`  
**Feeds:** IR evaluation and security testing.

The Dubai query source file has no timestamp. Year/month/day/time columns are filled by the pipeline so the mandatory set is complete.

| Column | Purpose |
|--------|---------|
| `Query_ID` | Unique log ID (`QRY…`). |
| `User_ID` | Stakeholder who issued the query. |
| `Query_Text` | Natural-language prompt. |
| `Log_Year` | Year received. |
| `Log_Month` | Month (1–12). |
| `Log_Quarter` | `Q1`–`Q4`. |
| `Log_Date` | Day of month (1–31). |
| `Log_Day` | Weekday name. |
| `Log_Time` | Time (`HH:MM:SS`). |
| `Retrieved_Document_IDs` | IDs the IR engine returned. |
| `Agent_Response` | LLM / agent output. |
| `Confidence_Score` | Retrieval / relevance score. |
| `Flagged_Suspicious` | Prompt-injection or unauthorized-access flag. |

---

## What is real vs generated

Present this distinction clearly:

| From source data | Enriched or generated for the project |
|------------------|----------------------------------------|
| Transaction IDs, dates, area, worth, property type/usage | Owner names, NIC, wallets |
| Area / project / landmark (DLD) | Title deed numbers, survey plans, boundaries |
| User IDs, roles, KYC (stakeholder files) | Notary / witness names, fees, deed text |
| Query text and relevance scores | Blockchain hashes, signatures, block numbers |

Do not claim prototype blockchain fields came from the Dubai Land Department CSV.
