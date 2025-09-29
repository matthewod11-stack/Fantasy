# PRD: Fantasy Football TikTok Content Engine  
*(v1.7 — Expanded Content Categories + Full Tech)*

---

## 1. Problem Statement
Independent creators lack a scalable way to consistently produce TikTok-native fantasy football content that is **timely, credible, and brand-safe** while also preparing monetization hooks for future growth.  

This project builds a **multi-agent content engine** with **human-in-the-loop oversight**, optimized for **TikTok distribution only**, with one human operator working ≤1 hour/day.

---

## 2. Goals & Objectives
- Produce 2–3 TikToks/day, scheduled weekly in one batch.  
- Limit human involvement to **one hour/day**, with primary batch-work on Tuesdays.  
- Build a retention loop: TikTok → Free Waiver Tiers sheet → Email → Future sponsors/affiliates.  
- Establish sponsor/affiliate infrastructure early (lightweight, not activated until scale).  
- Lay guardrails for AI agents to prevent off-brand or inaccurate posts.  
- Create lightweight testing + tracking mechanisms (Google Sheets-based).  
- Build with exit/sale potential in mind.  

---

## 3. Personas
- **Operator (you):** Sole creator, one hour/day max, hands-on for script approvals, scheduling, tracking.  
- **Audience:** Fantasy football players (18–34, TikTok-first). Want quick, punchy, trustworthy weekly advice.  
- **Future Sponsors:** DFS platforms, sportsbooks (where legal), sports apparel/gear, consumer brands.  

---

## 4. Functional Requirements

### 4.1 TikTok-Only Distribution
- All content outputs 9:16, 1080×1920, 15–30s runtime.  
- Music pulled from TikTok Commercial Music Library if possible during generation; fallback = add during scheduling.  
- Titles and thumbnails must follow industry best practices:  
  - Titles: “Start/Sit Week 5: Bijan Robinson”  
  - Thumbnails: Bold text + player face/jersey + team colors.  

### 4.2 Batch Generation Workflow
- CLI generates full week of content (10–15 posts).  
- Each bundle = `script.md`, `caption.txt`, `post.json`, `video.mp4`.  
- Operator reviews scripts/videos on Tuesday → approves → scheduled via TikTok Business Suite.  
- Videos drip-post throughout the week (2–3/day).  

### 4.3 Community Retention Loop
- TikTok posts CTA: “Download this week’s Waiver Tiers free in bio.”  
- Link-in-bio → Landing page → Waiver Tiers sheet (Google Sheets, Notion, or Substack).  
- Captures email on download.  
- Weekly cadence:  
  - Tuesday: New Waiver Tiers posted + emailed to list.  
  - TikTok anchors around Waiver Sheet (3 posts highlight it directly).  
  - Audience who joins email list gets “premium-feel” but still free content.  

### 4.4 Tracking & Attribution
- **Google Sheets Dashboard** with:  
  - Post ID / Date / Player / Type.  
  - TikTok stats: Views, Likes, Comments, Shares, Retention % at 3s/10s.  
  - Link CTR (from bio).  
  - Email signups per week.  
- **Attribution Framework:**  
  - Track CTR → Email signups (manual entry from landing page analytics).  
  - Tag each week’s Waiver Sheet link with UTM codes so you know which week drove conversions.  
- Operator updates sheet every Friday (~15 min).  

### 4.5 Monetization Infrastructure (future-ready)
- **Affiliate Slots:** Captions and Waiver Sheet footers must allow affiliate links.  
- **Sponsor Kit Workflow:** Living doc auto-pulls Google Sheet stats into a sponsor-facing template (views, demos, engagement rates).  
- **Ad Revenue:** Monitor TikTok Creator Fund / ad revenue once scale achieved.  
- No paid tier focus yet; keep only free + affiliate/sponsor-ready infrastructure.  

### 4.6 Content Categories (Expanded)
The Script Agent must support templates for the following categories:

1. Waiver Wire Gems (adds/drops)  
2. Start/Sit Lightning (weekly lineup decisions)  
3. Injury Pivots (status updates, replacements)  
4. Trade Thermometer (buy/sell/hold)  
5. Top Performers of the Week (studs + surprise breakouts)  
6. Biggest Busts (weekly or season-long underperformers)  
7. Breakout Tracker (rookie or rising star highlights)  
8. Consistency Kings (reliable producers)  
9. Injury Report Rundowns (weekly updates in bulk)  
10. Coaching/Playcalling Changes (impact on player usage)  
11. Depth Chart Shifts (new starters, bench demotions)  
12. Suspension/Return Watch (impact of returning players)  
13. Usage & Trends (target shares, snaps, red zone work)  
14. Matchup Exploits (players to target vs weak defenses)  
15. Rest-of-Season Outlooks (trajectory updates)  
16. Playoff Prep (schedule strength starting ~Week 10)  
17. Fantasy Awards/Memes (light, viral engagement content)  
18. Polls & Hot Takes (TikTok-native engagement plays)  
19. Q&A Replies (comment → video response loop)  
20. Weekly Wraps/Previews (Sunday recaps, TNF/MNF previews).  

**Template Requirements**  
- Each content type must have:  
  - Hook line (grabs attention in 3s)  
  - Context (stats/news)  
  - Action (what the viewer should do/think)  
  - Risk qualifier (so advice feels balanced)  
  - Outro/CTA  

**Batching Support**  
- CLI must allow:  
  - `--type performers --week 5`  
  - `--type busts --season`  
  - `--type coaching-change --team MIN`  
- Each type maps to a specific template under `/templates/script_templates/`.  

---

## 5. Non-Functional Requirements

- **Guardrails:**  
  - Never recommend players flagged as OUT.  
  - Avoid explicit betting/gambling calls unless flagged in config.  
  - Limit scripts to <70 words.  
  - Tone: Informative, conversational, energetic.  
- **Testing Infrastructure:**  
  - Weekly batch sanity check: Compare script length, word pacing, hashtags against templates.  
  - Spot-check 2–3 posts with actual playtesting before full batch scheduled.  
- **Aesthetic:**  
  - Visual style = Barstool / Bleacher Report adjacent (bold, sporty, clean).  
  - Fonts: Bold sans-serif.  
  - Colors: Team color pops + dark neutral backgrounds.  

---

## 6. Success Metrics
- **Content throughput:** ≥15 posts/week.  
- **Audience growth:** 0 → 10k followers in 90 days.  
- **Retention:** ≥70% watch at 10s, ≥40% full completion.  
- **Engagement:** ≥10% engagement rate per post.  
- **Email funnel:** ≥10% of followers join weekly Waiver Tiers list.  
- **Monetization readiness:** Sponsor kit live by 90 days.  

---

## 7. Daily Flow (≤1 Hour/Day, Batch on Tuesday)

**Tuesday (2 hours, batch day)**  
1. Run CLI → generate full week’s content.  
2. Approve/edit scripts interactively.  
3. Render videos, review outputs.  
4. Schedule all posts in TikTok Business Suite.  
5. Update Waiver Tiers sheet + email blast.  

**Wednesday–Monday (~15 min/day)**  
1. Monitor TikTok comments; reply to 5–10 top ones (optionally with reply videos).  
2. Update Google Sheet with stats (Friday).  
3. Check for anomalies (wrong player, missing tags).  

---

## 8. Roadmap (Updated)

**Phase 0 (Pre-MVP)**  
- Select avatar look/voice/style.  
- Run 2-week test (3 styles × 3 videos each).  
- Lock Season 1 avatar.  

**Phase 1 (Weeks 1–4)**  
- Batch content generation → TikTok posting.  
- Waiver Tiers → landing page → email capture.  
- Manual Google Sheets tracking + sponsor kit skeleton.  

**Phase 2 (Weeks 5–8)**  
- Wire **Sleeper API** for real player stats.  
- Integrate music at generation step.  
- Light sponsor outreach with performance kit.  

**Phase 3 (Month 3–4)**  
- Add second avatar (if 1st running smoothly for ≥1 month).  
- Test affiliate links in Waiver Tiers sheet.  
- Explore ad revenue + sponsorship.  

---

## 9. Exit Strategy
- Build brand value in TikTok channel + email list.  
- Revenue mix (affiliate + sponsor + ad) makes channel salable.  
- Target buyer = sports media startup, fantasy platform, or betting affiliate network.  

---

## 10. Technical Implementation (AI Agent System)

### 10.1 System Overview
Multi-agent architecture producing TikTok-ready bundles:  
- **Agents:** Data → Script → Avatar → Packaging → Human Approval  
- **Contract:** `/outputs/<slug>/` with script.md, caption.txt, post.json, video.mp4  

### 10.2 Agents
- **Data Agent:** Pulls stats (Sleeper API or CSV), flags injuries.  
- **Script Agent:** Jinja templates for 20 content categories.  
- **Avatar Agent:** Renders talking-head MP4 (HeyGen/D-ID API).  
- **Packaging Agent:** Bundles captions, hashtags, metadata.  
- **Human Approval:** Y/N step before video render.  

### 10.3 Testing & QA Infrastructure
- Unit tests (data validation, script word count).  
- Batch sanity checks.  
- Smoke tests with `--dry-run`.  

### 10.4 Tech Stack
- Python 3.11, jinja2, requests, pydantic  
- Sleeper API, HeyGen/D-ID API  
- Config-driven JSON/YAML  

### 10.5 Guardrails
- No OUT players.  
- No >70 word scripts.  
- No NSFW language.  
- Betting calls gated behind config.  

### 10.6 Batch Workflow
Weekly Tuesday batch, interactive approval, sequential renders, schedule posts.  

### 10.7 Lightweight Attribution Framework
Google Sheets dashboard, UTM links, manual Friday updates.  

### 10.8 Exit-Safe Engineering
Modular, config-driven, sponsor kit auto-generated.  

---

## 11. Sleeper API Integration Plan

### 11.1 Purpose
Replace static CSV with **live player data** from Sleeper API for accuracy and timeliness.  

### 11.2 Key Endpoints
- **Players Metadata:**  
  - Endpoint: `https://api.sleeper.app/v1/players/nfl`  
  - Returns: player_id, name, position, team, status (active, out, IR).  
- **Stats (Weekly):**  
  - Endpoint: `https://api.sleeper.app/v1/stats/nfl/regular/{year}/{week}`  
  - Returns: targets, receptions, carries, yards, TDs.  
- **Projections:**  
  - Endpoint: `https://api.sleeper.app/v1/projections/nfl/regular/{year}/{week}`  
  - Returns: projected points, usage share.  

### 11.3 Data Flow
1. **Input:** `--player "Bijan Robinson" --week 5`  
2. Data Agent → query Sleeper endpoints.  
3. Normalize fields → `player.json`:  
   ```json
   {
     "name": "Bijan Robinson",
     "team": "ATL",
     "pos": "RB",
     "status": "active",
     "rostered_pct": 98,
     "targets_last2w": 14,
     "notes": "Red zone usage trending up"
   }
   ```  
4. Pass JSON into Script Agent template.  

### 11.4 Guardrails
- If `status = OUT`, block script generation.  
- If missing projection data, fallback to baseline template.  
- Cap API calls: cache player metadata daily; fetch stats/projections weekly.  

### 11.5 Example Usage
```bash
ff-post --player "Bijan Robinson" --week 5 --type start-sit
```  
→ Data Agent calls Sleeper API → Script Agent drafts script with up-to-date stats.  

### 11.6 Testing
- Mock API responses in unit tests.  
- Validate schema: all numeric fields present.  
- Compare output to ESPN box scores weekly as a sanity check.  

---
