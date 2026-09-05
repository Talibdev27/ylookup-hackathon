# TRUSS — Frontend PRD & Build Prompt

## 1. Product Overview

**Project name:** TRUSS

TRUSS is a modern fintech/private-markets workspace connecting **Investors** and **Fund Managers** through shared company financial workspaces.

The core problem is the traditional workflow:

`Email / calls / messages → PDF or image → manual review → copy into Excel → reconcile → send corrections → repeat`

TRUSS replaces this with:

`Upload → AI extraction → Structured financial data → AI review → Human approval → Shared workspace → Excel`

Users can upload financial documents in multiple formats, including:

- PDF
- JPG
- PNG
- Screenshots
- Excel
- CSV

For the current MVP, the main financial document categories are:

1. Balance Sheet
2. Income Statement
3. Cash Flow Statement

The original uploaded file is processed by the backend and converted into structured financial spreadsheet data. The frontend should make the **generated spreadsheet** the primary object the user interacts with, rather than the original PDF/image.

---

# 2. Frontend Goal

Build a polished, production-quality web application for TRUSS.

The frontend should feel like a combination of:

- premium fintech platform
- modern banking application
- Dropbox/document workspace
- Linear
- Notion
- modern financial terminal

Do **not** make it look like a generic admin dashboard.

The interface should be:

- clean
- minimal
- sophisticated
- highly readable
- modern
- professional
- visually memorable
- responsive
- fast

Use interesting geometric details, refined shapes, elegant buttons, subtle animations and excellent spacing without making the interface visually noisy.

---

# 3. Technology

Frontend:

- Node.js
- React / Next.js
- TypeScript
- Tailwind CSS
- modern CSS
- reusable components

Structure the application so the mock frontend can later connect directly to a real backend API.

Do not hard-code the application into one giant component.

Use reusable components and clear page-level structure.

---

# 4. Core Information Architecture

TRUSS has two user roles:

## Investor

`Investor Dashboard → Company → Shared Company Workspace`

## Fund Manager

`Fund Manager Dashboard → Investor → Company → Shared Company Workspace`

The most important architectural concept:

### Two doors, one room.

Both Investors and Fund Managers eventually enter the **same Company Workspace**.

Do not build two separate versions of the Company Workspace.

Only the entry point and permissions differ.

---

# 5. Investor Dashboard

The Investor's first page should closely follow the uploaded whiteboard reference.

Keep this page intentionally simple.

The first screen should primarily contain:

1. Document Dropbox
2. Investor information/profile
3. Current investments

Do NOT add large portfolio charts, complicated analytics, or unnecessary dashboard cards.

---

## 5.1 Investor Header

Display:

**TRUSS**

Optional small product descriptor:

`Financial data, structured.`

Top-right:

- Profile icon
- Investor Info
- Settings

The profile area should be compact.

Clicking the profile icon opens an organisation/profile panel.

Show:

- Organisation name
- Organisation ID
- Contact information
- Total investment value
- Number of investments
- Settings

---

# 6. Investor Dropbox

The Dropbox is the central action of the Investor Dashboard.

Visual concept:

```text
┌──────────────────────────────────────────────────┐
│                                                  │
│  Dropbox                          ↓              │
│                                                  │
│        Drop financial documents here             │
│                                                  │
│        PDF · JPG · PNG · Screenshots             │
│                                                  │
│              [ Browse files ]                    │
│                                                  │
└──────────────────────────────────────────────────┘
```

Create a premium drag-and-drop upload area.

The upload zone should have:

- distinctive upload icon
- subtle geometric shapes
- elegant border
- hover state
- drag-over state
- smooth animation
- clear supported-format text

Primary action:

`Drop your financial documents here`

Secondary action:

`Browse files`

Supported input:

- PDF
- JPG
- PNG
- Screenshots
- Excel
- CSV

Do not make the UI PDF-specific.

---

# 7. Upload Processing State

After the user uploads a file, show a clear processing sequence.

Example:

```text
Uploading
   ↓
Reading document
   ↓
Extracting financial data
   ↓
Structuring spreadsheet
   ↓
AI validation
   ↓
Ready ✓
```

Use an elegant progress animation.

The backend will eventually perform the actual processing.

For the frontend MVP, use realistic mock processing states.

After processing, the file becomes associated with:

- Balance Sheet
- Income Statement
- Cash Flow Statement

The processed result should be represented as structured spreadsheet data.

---

# 8. Investor Investments

Under the Dropbox, display:

**Your Investments**

Use a clean list rather than large cards.

Example:

```text
01  Company A
02  Company B
03  Company C
```

Optionally show:

- current investment value
- status
- last updated

Example:

```text
Company A
£540,000
Active
Updated 2 Sep 2026
```

Each company is clickable.

Clicking:

`Company A`

opens:

`Company Workspace`

---

# 9. Company Workspace

This is the most important page in TRUSS.

The workspace should closely follow the uploaded whiteboard reference.

The structure is:

```text
Company
   ↓
Document navigation
   ↓
Recent uploads | Financial spreadsheet | AI Agent
```

---

## 9.1 Company Header

At the top:

`← Back`

Then:

**Company A**

`Technology`

Show:

`Current Investment: £540,000`

`Last updated: 5 September 2026`

Top-right:

`+ Upload Document`

Keep the header clean.

---

# 10. Company Navigation Bar

Immediately below the company header, create the main document navigation.

The navigation should closely resemble the whiteboard:

```text
┌──────────────────────────────────────────────────────────┐
│ Excel Spreadsheet │ Balance Sheet │ Cash Flow │ Income   │
│                   │                │           │ Statement│
└──────────────────────────────────────────────────────────┘
```

Use these sections:

- Excel Spreadsheet
- Balance Sheet
- Cash Flow Statement
- Income Statement
- Documents
- AI Review

The three financial document types are the core categories:

1. Balance Sheet
2. Cash Flow Statement
3. Income Statement

The active tab should have a clear but elegant visual treatment.

Use:

- subtle background
- rounded active state
- small icons
- hover states
- smooth transitions

Do not make the navigation oversized.

---

# 11. Company Workspace Layout

Below the navigation, use a three-column structure.

```text
┌──────────────┬───────────────────────────────┬──────────────┐
│              │                               │              │
│ Recent       │       Spreadsheet             │   AI Agent   │
│ Uploads      │                               │              │
│              │                               │              │
│ 1. Q2        │       Financial Data          │   Analysis   │
│ 2. Q1        │       Table                   │              │
│ 3. Annual    │                               │   Issues     │
│ 4. Q4        │                               │              │
│              │                               │ Suggestions  │
└──────────────┴───────────────────────────────┴──────────────┘
```

Suggested proportions:

- Left: 20–24%
- Centre: 52–58%
- Right: 22–26%

The centre spreadsheet is the main focus.

---

# 12. Recent Uploads Panel

Left panel title:

**Recent Uploads**

Display approximately the last 5–10 processed documents.

Example:

```text
Q2 2026 Statement
2 Sep 2026
✓ Verified

Q1 2026 Statement
4 Aug 2026
✓ Verified

Annual Statement
12 Jul 2026
⚠ Needs Review

Q4 2025 Statement
8 Apr 2026
✓ Verified
```

Each upload should show:

- document name
- date
- status
- source format

Example:

`Source: PDF`

or:

`Source: JPG`

or:

`Source: Screenshot`

The original upload format is metadata.

The main representation is the generated spreadsheet.

---

# 13. Important Document Behaviour

When a user uploads:

`PDF / JPG / PNG / Screenshot`

the system conceptually performs:

```text
Original File
      ↓
AI Processing
      ↓
Structured Financial Data
      ↓
Spreadsheet
```

When the user clicks a recent upload:

### Open the generated spreadsheet.

Do NOT open the original PDF/image by default.

The original source can be available through:

`View Source`

This is important to the product experience.

TRUSS is not primarily a PDF viewer.

TRUSS turns messy financial documents into usable structured financial data.

---

# 14. Financial Spreadsheet View

The centre of the workspace should contain a beautiful spreadsheet-style data viewer.

It should feel familiar to Excel users but much more modern.

Example:

## BALANCE SHEET
### Q2 2026

| Financial Metric | Q2 2026 | Q1 2026 | Change |
|---|---:|---:|---:|
| Cash | £482,000 | £431,000 | +11.8% |
| Receivables | £210,000 | £188,000 | +11.7% |
| Total Assets | £2.8M | £2.5M | +12.0% |
| Liabilities | £1.1M | £980K | +12.2% |
| Equity | £1.7M | £1.5M | +13.3% |

Include:

- search
- filters
- sorting
- column alignment
- number formatting
- currency formatting
- subtle row hover
- export button

Top-right:

`Export Excel`

The spreadsheet should be the dominant visual element.

---

# 15. Excel Export

Provide:

`Export Excel`

The generated spreadsheet should conceptually represent the structured financial data produced by the backend.

The frontend should be ready to call a backend endpoint such as:

`GET /documents/{document_id}/excel`

or:

`POST /documents/{document_id}/export`

For now, use mock data and a mock export action if the backend does not exist.

---

# 16. AI Agent Panel

The AI Agent should occupy the right side of the Company Workspace.

Do not make it look like ChatGPT.

It should look like an intelligent financial analyst.

Header:

**AI Agent**

Status:

`● Monitoring`

Then:

### Analysis

```text
✓ Document analysed

✓ Numbers extracted

✓ Previous period compared

⚠ 2 issues found
```

---

## 16.1 AI Issues

Example:

### Revenue discrepancy

Current:

`£1.24M`

Previous:

`£1.18M`

Change:

`+5.1%`

AI explanation:

`Revenue increased by 5.1% compared with the previous statement. Review supporting documentation.`

Button:

`View Issue`

---

### Cash movement

`Cash decreased by 18% despite increased revenue.`

Button:

`View Issue`

---

## 16.2 AI Suggestions

Section:

**Suggestions**

Examples:

- Review unusual revenue movement
- Confirm cash-flow classification
- Compare against previous quarter

The AI should focus on:

- discrepancies
- unusual changes
- missing information
- inconsistent numbers
- documents requiring attention
- useful financial observations

Do not overwhelm the user with AI text.

Keep it concise.

---

# 17. Status System

Use a consistent status system across the application.

Statuses:

### Verified
`✓ Verified`

### Needs Review
`⚠ Needs Review`

### Processing
`⟳ Processing`

### Uploaded
`● Uploaded`

### Critical
`🔴 Critical`

Use subtle, professional visual indicators.

Avoid overly bright warning colours or excessive badges.

---

# 18. Source Traceability

Every extracted financial number should conceptually be traceable to its source document.

Example:

```text
Revenue
£1,240,000

AI confidence
98%

Source:
Q2_Statement.pdf
Page 4
```

Include:

`View Source`

The user can open the original document if they need to verify the extracted value.

This creates the visual concept:

```text
Spreadsheet number
      ↓
AI extraction
      ↓
Original source
```

---

# 19. File Detail Interaction

When a user opens a financial document:

Show:

### Main area
Generated spreadsheet

### Metadata
- document name
- financial document type
- upload date
- source format
- AI confidence
- processing status

Actions:

`Export Excel`

`View Source`

`AI Review`

`Approve`

`Flag Issue`

The generated spreadsheet remains the primary view.

---

# 20. Fund Manager Dashboard

The Fund Manager side should closely follow the uploaded whiteboard.

Keep it intentionally simple.

The Fund Manager's first page is a relationship/navigation page.

It should communicate:

```text
Fund Manager
      ↓
Investors
      ↓
Companies
      ↓
Shared Company Workspace
```

Do NOT create a large analytics dashboard.

---

# 21. Fund Manager Header

Title:

**Fund Manager**

Subtitle:

`Manage investors and review their financial data.`

Top-right:

- Profile icon
- Fund Manager Info
- Settings

---

# 22. Fund Manager Investor List

Main section:

**My Investors**

Display investors vertically.

Example:

```text
01  Investor A
02  Investor B
03  Investor C
```

Each investor is clickable.

When expanded, reveal associated companies.

Example:

```text
Investor A
   ├── Company A
   ├── Company B
   └── Company C

Investor B
   ├── Company D
   └── Company E

Investor C
   └── Company F
```

Use subtle connecting lines and indentation to make the relationship obvious.

This should visually reflect the uploaded whiteboard.

---

# 23. Fund Manager Interaction

Click:

`Investor A`

↓

Expand:

```text
Investor A

Company A
Company B
Company C
```

Click:

`Company A`

↓

Open:

**Company A Workspace**

This must be the SAME Company Workspace that an Investor sees.

Do not duplicate the UI.

---

# 24. Shared Company Workspace

The core architecture:

```text
                  Company A
                     │
          ┌──────────┴──────────┐
          │                     │
      Investor              Fund Manager
          │                     │
          └──────────┬──────────┘
                     ↓
              SAME WORKSPACE
                     │
          ┌──────────┼──────────┐
          ↓          ↓          ↓
      Documents  Spreadsheet  AI Agent
```

Both users should see the same underlying financial information, subject to permissions.

---

# 25. Navigation Philosophy

Avoid a huge sidebar on the Investor first screen.

The first Investor page should focus on:

`Dropbox + Investments + Profile`

The Fund Manager first page should focus on:

`Investors + Companies + Profile`

Once a company is selected, the Company Workspace navigation becomes the main navigation.

This keeps the user journey simple.

---

# 26. Responsive Design

The application must work beautifully on:

- desktop
- laptop
- tablet
- mobile

Mobile behaviour:

### Investor Dashboard
- Dropbox remains the main action
- investment list becomes full-width
- profile becomes a compact menu

### Company Workspace
- three columns collapse into a logical vertical layout
- Recent Uploads becomes a horizontal/expandable section
- spreadsheet becomes horizontally scrollable
- AI Agent becomes a drawer or expandable bottom panel

### Fund Manager
- investors become full-width expandable rows
- company hierarchy remains easy to understand

---

# 27. Visual Language

Use a distinctive but restrained visual identity for **TRUSS**.

The name should inspire the idea of:

- structure
- connection
- support
- trust
- financial infrastructure

Visual details can subtly reference structural/geometric forms.

Use:

- clean lines
- subtle grids
- refined geometric shapes
- elegant containers
- subtle shadows
- sophisticated typography
- polished buttons
- small micro-interactions

Do not make the interface overly futuristic.

The product should feel trustworthy enough for financial professionals.

---

# 28. Animation

Use subtle animations for:

- page transitions
- upload processing
- drag-and-drop
- expanding investors
- opening companies
- AI analysis
- status changes
- spreadsheet interactions

Animations should be fast and purposeful.

Do not use excessive motion.

---

# 29. Mock Data

Use realistic mock data.

Example investors:

- Investor A
- Investor B
- Investor C

Example companies:

- Company A
- Company B
- Company C
- Company D
- Company E

Example financial data:

- Revenue
- Operating Expenses
- Net Income
- Cash
- Assets
- Liabilities
- Equity
- Receivables

Use GBP where appropriate.

---

# 30. Frontend Routes

Suggested routes:

```text
/
 /login

/investor
/investor/company/[companyId]

/fund-manager
/fund-manager/investor/[investorId]
/fund-manager/company/[companyId]

/company/[companyId]/balance-sheet
/company/[companyId]/income-statement
/company/[companyId]/cash-flow
/company/[companyId]/documents
/company/[companyId]/ai-review

/document/[documentId]
```

The exact routing architecture can be adjusted if a cleaner implementation is preferred.

---

# 31. Reusable Components

Create reusable components such as:

```text
AppHeader
ProfileMenu
UploadDropzone
UploadProgress
InvestmentList
InvestorList
CompanyList
InvestorRow
CompanyRow
CompanyHeader
DocumentTabs
RecentUploads
DocumentItem
SpreadsheetViewer
FinancialTable
AIAgentPanel
AIInsight
IssueCard
StatusBadge
SourceTrace
ExportButton
ReviewButton
```

Keep components modular.

---

# 32. Backend Integration Preparation

The frontend should be structured to connect to APIs later.

Potential API endpoints:

```text
POST /documents/upload

GET /companies

GET /companies/{company_id}

GET /companies/{company_id}/documents

GET /documents/{document_id}

GET /documents/{document_id}/financial-data

GET /documents/{document_id}/analysis

GET /documents/{document_id}/excel

POST /documents/{document_id}/approve

POST /documents/{document_id}/flag

GET /investors

GET /investors/{investor_id}/companies
```

For the frontend-only MVP, use mock API/data services.

Do not couple the UI directly to static hard-coded objects everywhere.

---

# 33. Core Demo Journey

The UI should be designed around this hackathon demo.

## Investor

1. Investor logs in.
2. Investor sees Dropbox.
3. Investor drops a screenshot/PDF.
4. Processing animation appears.
5. AI extracts the financial information.
6. Document is classified as Balance Sheet, Income Statement or Cash Flow Statement.
7. Structured spreadsheet appears.
8. Investor opens the generated spreadsheet.
9. AI Agent identifies a discrepancy.
10. Investor opens the issue.
11. AI explains the issue.
12. Investor can view the source.
13. Investor approves the result.

## Fund Manager

1. Fund Manager logs in.
2. Sees Investor A, Investor B, Investor C.
3. Expands Investor A.
4. Sees Company A, Company B and Company C.
5. Clicks Company A.
6. The SAME Company A Workspace opens.
7. Fund Manager sees the same structured financial information and AI review.

---

# 34. Critical Product Principle

Do not pitch or visually represent TRUSS as:

`PDF → Excel converter`

That is only one part of the system.

The frontend should communicate:

**Unstructured financial documents → structured financial data → AI review → shared financial workspace**

Excel is an output and interaction format.

The bigger product is a shared financial data layer between Investors and Fund Managers.

---

# 35. What NOT to Build

Keep the MVP focused.

Do NOT build:

- payments
- messaging
- video calls
- complicated accounting
- full ERP
- complex portfolio analytics
- trading
- dozens of financial metrics
- complicated permissions
- unnecessary charts
- giant AI chatbot
- complicated notification centre

The product should have one extremely clear workflow:

**UPLOAD → EXTRACT → STRUCTURE → REVIEW → APPROVE → SHARE**

---

# 36. Final UI Principle

The application should feel immediately understandable.

Within 5 seconds, a new user should understand:

### Investor

`I can drop my financial documents here.`

`I can see my investments below.`

### Fund Manager

`I can see my investors.`

`I can open their companies.`

### Company Workspace

`I can see the financial spreadsheet.`

`I can see recent documents.`

`The AI tells me what needs attention.`

That simplicity is more important than adding more features.

---

# FINAL BUILD INSTRUCTION

Build TRUSS as a polished, production-quality fintech web application using Node.js, React/Next.js, TypeScript, Tailwind CSS and modern CSS.

Use the uploaded whiteboard images as visual/structural references.

Preserve the whiteboard concepts:

**Investor:**

`Dropbox → Investments → Company`

**Fund Manager:**

`Investors → Companies → Company`

**Company:**

`Recent Uploads → Spreadsheet → AI Agent`

Turn these simple hand-drawn concepts into a sophisticated, responsive and visually memorable interface.

The UI should be impressive enough for a Ylookup × Encode AI hackathon demo while remaining simple enough that an investor or fund manager can understand it immediately.

The product's visual story is:

**Messy financial documents go in.  
Structured, reviewable financial data comes out.  
Investors and Fund Managers share one source of truth.**
