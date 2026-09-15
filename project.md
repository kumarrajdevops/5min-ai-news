Below is the **full architecture baseline** we have defined for the project, incorporating the latest decisions: **AI-only news, daily 6 AM IST publication, 30 candidates → Top 25 + 5 backups, human approval, one avatar/voice, YouTube + Instagram, local first → AWS → Kubernetes, and cost-controlled scheduled processing.**

# AI News — Full Architecture

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                         AI TECHNOLOGY NEWS PLATFORM                           │
└──────────────────────────────────────────────────────────────────────────────┘

                              NEWS SOURCES
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
        RSS / Websites        News APIs            Social / Video
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │ NEWS INGESTION    │
                         │ Python Workers    │
                         └─────────┬─────────┘
                                   │
                         Raw articles/events
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │      RAW NEWS STORE      │
                    │ PostgreSQL + Object Store │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ NORMALIZATION             │
                    │ • Extract article         │
                    │ • Clean content           │
                    │ • Normalize metadata      │
                    │ • Timestamp               │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ DEDUPLICATION             │
                    │ • Same story detection    │
                    │ • Similarity matching     │
                    │ • Source grouping         │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ AI RELEVANCE FILTER       │
                    │                            │
                    │ Is this AI technology?    │
                    └────────────┬─────────────┘
                                 │
                        AI-only stories
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ FACT EXTRACTION           │
                    │ • Claims                  │
                    │ • Dates                   │
                    │ • Companies               │
                    │ • Products                │
                    │ • Events                  │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ VERIFICATION ENGINE       │
                    │ • Source checking         │
                    │ • Cross-source validation │
                    │ • Confirmed-news only     │
                    └────────────┬─────────────┘
                                 │
                           Verified stories
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │       RANKING ENGINE      │
                    │                            │
                    │ • Recency                │
                    │ • Importance              │
                    │ • AI impact              │
                    │ • Audience interest      │
                    │ • Credibility            │
                    │ • Momentum               │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │      TOP 30 SELECTION     │
                    │                            │
                    │  #1  ───────────────┐     │
                    │  #2                │     │
                    │  ...               │     │
                    │  #25  ← PUBLISH     │     │
                    │  #26  ← BACKUP      │     │
                    │  ...               │     │
                    │  #30  ← BACKUP      │     │
                    └────────────┬─────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ EDITORIAL DASHBOARD      │
                    │                            │
                    │ Human reviews Top 30     │
                    │ • Edit story              │
                    │ • Change ranking          │
                    │ • Edit script             │
                    │ • Replace defective story │
                    │ • Approve / Reject        │
                    └────────────┬─────────────┘
                                 │
                          Approved Top 25
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ SCRIPT GENERATION         │
                    │                            │
                    │ Verified facts ONLY       │
                    │ • Headline                │
                    │ • Summary                 │
                    │ • Why it matters          │
                    │ • Source reference        │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ VOICE GENERATION          │
                    │                            │
                    │ One branded AI voice      │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ VISUAL / ASSET ENGINE     │
                    │                            │
                    │ • Avatar                  │
                    │ • News visuals            │
                    │ • Screenshots             │
                    │ • Generated visuals       │
                    │ • Motion graphics         │
                    │ • Background music        │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ VIDEO COMPOSITION         │
                    │                            │
                    │ Voice + Visuals + Avatar  │
                    │ + Captions + Branding     │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ AUTOMATED VIDEO QA        │
                    │                            │
                    │ ✓ Exactly 25 stories      │
                    │ ✓ AI-only                │
                    │ ✓ Verified sources       │
                    │ ✓ Captions               │
                    │ ✓ Audio                  │
                    │ ✓ Video integrity        │
                    │ ✓ Duration target        │
                    │ ✓ Source links           │
                    └────────────┬─────────────┘
                                 │
                           QA PASSED
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ FINAL HUMAN APPROVAL     │
                    │                            │
                    │       APPROVE / REJECT   │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │ MASTER VIDEO  │
                         └───────┬───────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
             ┌──────────────┐         ┌──────────────┐
             │   YOUTUBE    │         │  INSTAGRAM   │
             │              │         │              │
             │ Video       │         │ Video        │
             │ Title       │         │ Caption      │
             │ Description │         │ Hashtags     │
             │ Thumbnail   │         │ Source links │
             │ Chapters    │         │              │
             │ Source links│         │              │
             └──────┬───────┘         └──────┬───────┘
                    │                        │
                    └───────────┬────────────┘
                                ▼
                     ┌──────────────────────┐
                     │ ANALYTICS COLLECTION │
                     │                      │
                     │ Views                │
                     │ Retention            │
                     │ Watch time           │
                     │ Shares               │
                     │ Likes / Comments     │
                     │ Followers            │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │ OPTIMIZATION ENGINE  │
                     │                      │
                     │ Improve future       │
                     │ story ranking        │
                     └──────────────────────┘
```

# Daily Execution Architecture

The key point is that **we are NOT continuously collecting news 24/7**.

We use scheduled collection to control cost.

```text
                DAILY NEWS CYCLE — IST

10:00 PM ────────┐
                 │
                 ▼
            Collect AI News
                 │
1:00 AM ─────────┤
                 │
                 ▼
            Collect AI News
                 │
3:30 AM ─────────┤
                 │
                 ▼
          Final Collection
                 │
4:00 AM ─────────┘
                 │
                 ▼
          COLLECTION CUTOFF
                 │
                 ▼
       Process / Verify / Rank
                 │
                 ▼
          Select Top 30
                 │
                 ▼
       Top 25 + 5 Backups
                 │
                 ▼
         Generate Content
                 │
                 ▼
           Video Rendering
                 │
                 ▼
             Automated QA
                 │
                 ▼
          Human Approval
                 │
                 ▼
              6:00 AM
                 │
          ┌──────┴──────┐
          ▼             ▼
       YouTube       Instagram
```

The **10 PM, 1 AM and 3:30 AM times are implementation recommendations**, not immutable requirements. We can tune them after measuring how quickly the pipeline runs and how fresh the news needs to be.

# Top-30 Safety Mechanism

This is one of the most important design decisions.

We don't simply do:

```text
100 stories → Top 25 → Video
```

Instead:

```text
                     Candidate News
                          │
                          ▼
                   Filter + Verify
                          │
                          ▼
                  Qualified Stories
                          │
                          ▼
                       Rank
                          │
                          ▼
                    ┌──────────┐
                    │ Top 30   │
                    └────┬─────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
          #1–#25                 #26–#30
          PRIMARY                 BACKUP
              │                     │
              ▼                     │
        Editorial Review            │
              │                     │
        Defective?                  │
          │      │                  │
         YES     NO                 │
          │      │                  │
          └──────┘                  │
              │                     │
              └──── Replace ◄───────┘
                       │
                       ▼
                   FINAL 25
```

This means if story **#7 fails verification**, we can replace it with **#26** rather than rebuilding the entire episode.

# Technology Architecture

## Local MVP

```text
┌──────────────────────────────────────────┐
│              LOCAL MACHINE               │
│                                          │
│ Docker / Kubernetes                      │
│                                          │
│ ┌──────────┐     ┌──────────────────┐   │
│ │ FastAPI  │────►│ Workers          │   │
│ └──────────┘     │                  │   │
│                  │ Ingestion        │   │
│                  │ Processing       │   │
│                  │ Verification     │   │
│                  │ Ranking          │   │
│                  │ Script           │   │
│                  │ Voice            │   │
│                  │ Video            │   │
│                  │ Publishing       │   │
│                  └────────┬─────────┘   │
│                           │              │
│                    ┌──────┴──────┐       │
│                    ▼             ▼       │
│               PostgreSQL    Object Store │
│                                          │
│               Admin Dashboard            │
└──────────────────────────────────────────┘
```

## AWS Evolution

```text
                         AWS
                          │
                    EventBridge
                          │
                    Scheduled Jobs
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
      Ingestion        Processing       Publishing
       Workers           Workers          Workers
          │               │                │
          └───────────────┼────────────────┘
                          │
                   ┌──────┴──────┐
                   ▼             ▼
                 RDS             S3
             PostgreSQL       Media Store
                   │             │
                   └──────┬──────┘
                          │
                    Admin/API
                          │
                    Human Review
```

Later, when workload justifies it:

```text
                         AWS
                          │
                         EKS
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼
  API Services       Processing Pods    Video Workers
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                    Event / Queue
                          │
                 ┌────────┴────────┐
                 ▼                 ▼
                RDS               S3
```

# Persistent vs Ephemeral Compute

This is the cost principle we discussed.

### Persistent

```text
PostgreSQL
S3
Application data
Audit history
```

### Ephemeral

```text
News collection
AI processing
Verification
Ranking
Script generation
Video rendering
Publishing jobs
```

The idea is:

> **Start compute → execute job → save result → terminate compute.**

We don't want:

> **Start server → wait 20 hours → execute job → keep waiting.**

That becomes especially valuable on AWS.

# Core Application Components

The MVP should therefore have these logical components:

| Component               | Responsibility           |
| ----------------------- | ------------------------ |
| **API**                 | Backend API              |
| **Admin UI**            | Editorial control        |
| **News Collector**      | Retrieve news            |
| **Normalizer**          | Standardize articles     |
| **Deduplicator**        | Group duplicate stories  |
| **AI Classifier**       | Determine AI relevance   |
| **Fact Extractor**      | Extract factual claims   |
| **Verification Engine** | Confirm stories          |
| **Ranking Engine**      | Rank candidates          |
| **Top-30 Selector**     | Select 30                |
| **Backup Manager**      | Maintain 5 backups       |
| **Script Generator**    | Create fact-based script |
| **Voice Worker**        | Generate narration       |
| **Visual Worker**       | Prepare visuals          |
| **Video Worker**        | Render episode           |
| **QA Worker**           | Validate final episode   |
| **Publishing Worker**   | YouTube/Instagram        |
| **Analytics Worker**    | Collect performance      |
| **Notification Worker** | Send failure alerts      |

These are **logical boundaries initially**. They don't have to become 14 separate microservices immediately.

# Data Architecture

PostgreSQL stores the system of record:

```text
Sources
   │
   ├── Articles
   │      │
   │      └── Story Groups
   │              │
   │              ├── Verification
   │              ├── Ranking
   │              └── Sources
   │
   └── Episodes
          │
          ├── Top 25 Stories
          ├── Backup Stories
          ├── Script
          ├── Assets
          ├── Video
          ├── Approval
          └── Publication
```

Large files go to object storage:

```text
Object Storage
│
├── raw-news/
├── images/
├── avatar/
├── audio/
├── captions/
├── thumbnails/
└── videos/
```

# Quality & Audit Chain

Every published story should be traceable:

```text
SOURCE
  ↓
RAW ARTICLE
  ↓
NORMALIZED ARTICLE
  ↓
STORY
  ↓
VERIFIED FACTS
  ↓
RANKING
  ↓
TOP 25
  ↓
SCRIPT
  ↓
VIDEO
  ↓
HUMAN APPROVAL
  ↓
PUBLICATION
```

This is important because you explicitly want historical data retained for **future auditability**.

# Final Product Flow

The entire product can ultimately be summarized as:

```text
                  ┌──────────────────┐
                  │   AI NEWS WEB    │
                  │     SOURCES      │
                  └────────┬─────────┘
                           │
                     Scheduled
                     Collection
                           │
                           ▼
                  ┌──────────────────┐
                  │   NEWS ENGINE    │
                  │                  │
                  │ Filter           │
                  │ Deduplicate      │
                  │ Verify           │
                  │ Rank             │
                  └────────┬─────────┘
                           │
                     30 STORIES
                           │
                           ▼
                  ┌──────────────────┐
                  │ TOP 25 + 5 BACKUP│
                  └────────┬─────────┘
                           │
                     HUMAN REVIEW
                           │
                           ▼
                  ┌──────────────────┐
                  │ CONTENT ENGINE   │
                  │                  │
                  │ Script           │
                  │ Voice            │
                  │ Avatar           │
                  │ Visuals          │
                  │ Captions         │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │   VIDEO ENGINE   │
                  └────────┬─────────┘
                           │
                           ▼
                      AUTOMATED QA
                           │
                           ▼
                    HUMAN APPROVAL
                           │
                           ▼
                  ┌────────┴────────┐
                  ▼                 ▼
              YOUTUBE           INSTAGRAM
                  │                 │
                  └────────┬────────┘
                           ▼
                       ANALYTICS
                           │
                           ▼
                  RANKING OPTIMIZATION
```

## The final architecture principle

**Collect cheaply → process intelligently → verify aggressively → select 30 → publish exactly 25 → generate one branded video → human approval → distribute everywhere → measure → improve.**

And the implementation path remains:

**Local Prototype → Production MVP → AWS → Kubernetes/Enterprise**

This is now a solid baseline from which we can start building the actual system.
