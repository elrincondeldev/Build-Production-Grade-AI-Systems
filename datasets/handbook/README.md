# Kestrel Pay handbook (fictional)

The **docs-assistant** (Track B) answers questions from this corpus. Everything here is invented for teaching, including people, emails and phone numbers.

Every document has front matter with an `access` level. Module 5 uses it for **role-based retrieval**: users must only get answers from documents their role allows.

| Role | Can read access levels |
|---|---|
| `customer` | `public` |
| `employee` | `public`, `employee` |
| `engineer` | `public`, `employee`, `engineering` |
| `hr` | `public`, `employee`, `hr` |
| `finance` | `public`, `employee`, `finance` |

Two documents are deliberately "dirty" so you can practise production problems:

| File | Trap | Used in |
|---|---|---|
| `partner-faq.md` | Hidden **indirect prompt injection** in an HTML comment, uploaded by an external partner | Lessons 2.4 and 5.2 |
| `salary-bands.md` | Contains **PII** (name, email, phone) | Lesson 5.4 |
| `security-faq.html` | HTML with navigation and footer boilerplate that must be stripped | Lesson 2.4 |

The golden evaluation set lives in [`../golden/handbook_qa.jsonl`](../golden/handbook_qa.jsonl).
