# Changelog

All notable changes to the Smart DJ Music Assistant add-on.

## 0.0.24

- **Library-wide analysis sweep** — new `smart_dj/analyze_library_local` action
  (`start` / `status` / `cancel`): backfills the local ML analyzer for the whole
  library, no Musicae quota, audio never stored.
- **HA-stability safeguards**: the sweep pauses itself while any player is
  actively playing and resumes when idle; concurrency follows the streams
  background-scan setting (default 2, clamped 1-8); a circuit breaker aborts
  after 50 consecutive failures; cancel interrupts in-flight work cleanly;
  restarting the add-on cancels a running sweep.
- **Create playlist from analyzed tracks** — new `smart_dj/create_analyzed_playlist`
  action: builds a playlist out of every library track that HAS analysis data
  (a guaranteed ready-to-mix pool), with an optional `search` filter.
- **Frontend redesign**: queue rows now show the album art behind each track,
  Smart-DJ-added tracks are highlighted with chips + a toast, settings are
  collapsible sections, the Radio blend style is selectable, a library-search
  gap slot re-anchors the mix, and new Library-analysis controls (sweep progress
  + create-playlist) live in the view.

## 0.0.23

- Radio handover transition style (decks never blend; sequential crossfade).
- Segue-quality queue ordering in the optimizer.
- Per-genre transition profiles when blend style is on Auto.
- 8-bar phrase alignment for transitions.
- Boundary gain match (−3..+6 dB on the incoming deck, radio excluded).
- Background `smart_dj/analyze_playlist` sweep (local ML, no Musicae quota).

## 0.0.21

- First fork release with the Smart DJ provider, Musicae-backed analysis,
  queue intelligence actions, and the add-on scaffold.
