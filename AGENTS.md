# Project Documentation Guidelines

All critical documentation is stored in the `.agent` folder.  
This directory serves as the central source of truth for system knowledge and must be kept continuously updated.

---

## Folder Structure

**`.agent/`**
- **Tasks/** — Product Requirement Documents (PRD) and implementation plans for each feature.  
- **System/** — Comprehensive documentation of the current system state, including:
  - Project structure and technology stack  
  - Integration points  
  - Database schema  
  - Core functionalities (e.g., agent architecture, LLM layer, etc.)
- **SOP/** — Standard Operating Procedures and best practices for common tasks  
  (e.g., adding schema migrations, defining new page routes, etc.)
- **README.md** — An index and quick reference guide for all documentation, helping contributors locate relevant materials efficiently.

---

## Update Policy

Always update the `.agent` documentation after implementing or modifying a feature.  
This ensures the repository accurately reflects the system’s most up-to-date state and prevents knowledge drift.

---

## Before Implementation

Before starting any new feature or system change:
1. Read `.agent/README.md` to understand current architecture and context.  
2. Review related `Tasks`, `System`, or `SOP` documents.  
3. Confirm that your implementation plan aligns with existing standards and structures.