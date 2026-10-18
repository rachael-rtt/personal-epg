# Personal XMLTV EPG — setup in progress

Prepared for the uploaded playlist: 3,882 stream entries, 2,587 distinct guide IDs.
The original playlist is unchanged. Only channel names and IDs are included here;
stream URLs are not needed to generate the EPG and are not included.

## Current status

The merger and offline tests are ready. Live XML feeds could not be downloaded in
the preparation session. Full guide coverage, programme freshness, and publication
are NOT yet verified. No hosted feed URL exists yet.

Open-EPG's live country page was inspected on 18 October 2026. It listed 11 US
feeds, 7 Italian feeds, UK, Malta, and Australia feeds. The Australian source is
included because the uploaded playlist contains 54 Australian-tagged entries.
The US inventories include Pluto TV Comedy and Sitcom Legends in unitedstates9.
NBC Comedy Vault and SNL Vault were not found under those names in the 11 US
inventories. They require further source investigation; name-search absence does
not establish definitive absence under every possible alias.

Open-EPG uses IDs such as `Pluto TV Comedy.us`; the playlist uses
`PlutoTVComedy.us@US`. Simply concatenating the files will not match the playlist.
Two explicit seed mappings are included. All other IDs remain in channels.json
and will be audited. A report suggests name matches but never applies them
automatically. Regional IDs, plus-one channels, and local affiliates must be
reviewed individually. No percentage coverage claim has been made.

## One-time hosting setup

1. Create a free account at https://github.com/signup. Complete registration yourself.
2. Create a public repository named `personal-epg` (or choose another name).
3. Upload the CONTENTS of this folder, including `.github/workflows/refresh.yml`.
   Do not upload the original playlist. If the hidden .github folder is omitted by
   the upload dialog, use Add file → Create new file and enter the full path
   `.github/workflows/refresh.yml`, then paste its contents.
4. Open Actions → Refresh EPG → Run workflow. This first run is audit-only.
5. Download the `coverage-report` artifact. Review `coverage.json` and
   `source-channels.json`. Send these reports back to this chat so the remaining
   mappings and missing sources can be resolved before publication.
6. Once acceptable coverage is established, update mappings.json; set
   `minimum_covered_ids` to the approved covered count, add any essential IDs to
   `required_ids`, and set `coverage_reviewed` to true in config.json.
7. Open Settings → Pages → Build and deployment → Source → GitHub Actions.
8. Run Refresh EPG again. On success, use the Pages deployment URL followed by
   `/epg.xml` in TiviMate. The alternative is `/epg.xml.gz`.

The resulting address will have the form
`https://YOUR-USERNAME.github.io/personal-epg/epg.xml`; this is a template, not a live link.
GitHub Pages makes the output publicly accessible. The output contains guide
listings and channel IDs, not stream URLs. This is intended for personal use.

## Refresh and reliability

The schedule runs at 20:37 UTC daily (21:37 Malta winter / 22:37 summer), after
Open-EPG's stated daily update time. GitHub schedules may be delayed. In public
repositories scheduled workflows can be disabled after 60 days without repository
activity: keep the repository maintained and check Actions if the guide stops.
Enable GitHub failure notifications. This is low-maintenance, not unattended forever.

A source download or parse failure stops the build; no Pages deployment occurs,
so the last published feed remains available, but it will eventually become stale.
Successful updates below the reviewed coverage minimum also stop publication.
The public status.json shows when the last successful guide was built.
No retry loop repeatedly downloads the same feeds. Avoid unnecessary manual runs;
Open-EPG asks for one download daily and lists a 20-download/day public-file cap.

The merger detects gzip by content, limits expanded size, normalizes explicit time
offsets to UTC, outputs one channel per playlist ID, drops identical programme
duplicates, and chooses earlier configured sources for overlapping time slots.
Later sources fill non-overlapping gaps. Programmes with missing/ambiguous times,
non-positive duration, or no title are skipped and counted. Old listings outside
the retained window are removed. Listings with missing stop times are skipped
rather than inventing a duration. Coverage means at least one non-expired listing,
not proof that every hour is covered. Source definitions with duplicate IDs are
rejected for review. The same ID in different sources is assumed to mean the same
channel only for exact playlist ID matching; explicit mappings select one source.

## TiviMate

Keep your current playlist. Add the final XML URL under Settings → EPG → EPG
sources, enable it for the playlist, and update EPG. Use a 24-hour update interval.
Mappings rewrite XML channel/programme IDs to your current tvg-id values, so no
playlist editing is required. Unmatched channels retain their streams but have
no listings from this feed. No m3u4u import is needed for this direct TiviMate setup;
external m3u4u import capability has not been verified.

## Local commands (Python 3.11 or later)

Run from this folder:

    python -m unittest discover -s tests -v
    python merge_epg.py --audit
    python merge_epg.py

## References

- https://www.open-epg.com/app/epgguide.php
- https://www.open-epg.com/app/faq.php
- https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule

GitHub Free supports public-repository Pages. Published Pages sites have a 1 GB
size limit and 100 GB/month soft bandwidth limit; this setup is for personal
guide consumption. The upstream site currently warns of changes and instability.
