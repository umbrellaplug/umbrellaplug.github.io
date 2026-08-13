# Umbrella Provider Guide

*What each tracking service can actually do inside Umbrella — lists, progress tracking, dropped shows, and the bulk-management tools behind them.*

**Providers:** Trakt · Simkl · MDBList · Custom · Floppy · Scrob
**Legend:** ✅ Full support &nbsp;&nbsp; 🟡 Partial support &nbsp;&nbsp; — Not supported

---

## Lists & Tracking

| Capability | Trakt | Simkl | MDBList | Custom | Floppy | Scrob |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Watchlist | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Collection | ✅ | — | ✅ | ✅ | ✅ | — |
| Watched / History | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Dropped Shows [¹](#notes) | 🟡 | ✅ | 🟡 | ✅ | ✅ | — |
| On Hold / Watching status | — | 🟡 | — | — | ✅ | — |
| User / Liked Lists | ✅ | — | ✅ | ✅ | — | ✅ |

## Progress & Calendar

| Capability | Trakt | Simkl | MDBList | Custom | Floppy | Scrob |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Progress Shows | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Progress Episodes | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Upcoming Progress | ✅ | — | — | ✅ | ✅ | ✅ |
| Unfinished (Resume Points) | ✅ | — | ✅ | ✅ | ✅ | ✅ |
| Calendar (Recent / Upcoming / Premieres) | ✅ | — | ✅ | ✅ | — | — |

## Management Tools (Bulk Editors)

| Capability | Trakt | Simkl | MDBList | Custom | Floppy | Scrob |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Watchlist Manager | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Collection Manager | ✅ | — | ✅ | ✅ | ✅ | — |
| Dropped Manager [¹](#notes) | 🟡 | ✅ | 🟡 | ✅ | ✅ | — |
| On Hold Manager | — | 🟡 | — | — | — | — |
| Unfinished Manager | ✅ | — | ✅ | ✅ | ✅ | ✅ |
| Liked List Manager [²](#notes) | ✅ | — | — | — | — | — |

## Account & Sync

| Capability | Trakt | Simkl | MDBList | Custom | Floppy | Scrob |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Can Be Indicators / Scrobble Source | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Authorization Method [³](#notes) | `OAuth Device` | `OAuth PIN` | `OAuth Device` | `OAuth Device` | `Manual Token` | `Manual Token` |
| Force Sync Tool | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mark-Watched Passthrough | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

### Notes

1. **Dropped Shows / Dropped Manager** — Trakt has no browsable "Dropped" list; it relies on Trakt's native hidden-items feature to filter dropped shows out of Progress and Calendar automatically, managed through a toggle-based Hidden Progress Manager rather than a plain add/remove list. MDBList's Dropped is TV-only — no `movies_dropped` table exists anywhere in the addon.
2. **Liked List Manager** — MDBList's Liked Lists can be viewed but not un-liked from inside Umbrella; the provider only exposes a read endpoint, with no removal call to build a manager against.
3. **Authorization Method** — Trakt, MDBList, and Custom use a device-code flow (approve a code on the provider's own site); Simkl uses an equivalent PIN-based variant. Floppy and Scrob instead take a server URL and token pasted into settings, validated with a connection test rather than an interactive login.
