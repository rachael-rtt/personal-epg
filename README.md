# Personal TiviMate EPG

Feed: https://rachael-rtt.github.io/personal-epg/epg.xml
Compressed alternative: https://rachael-rtt.github.io/personal-epg/epg.xml.gz
Status and coverage: https://rachael-rtt.github.io/personal-epg/

Add the XML feed as an EPG source in TiviMate, assign it to your existing playlist, and update the EPG. Set TiviMate to update daily. Your original playlist remains unchanged. The repository contains channel names and IDs, not stream URLs.

## Coverage

The playlist has 3,882 entries and 2,587 distinct channel IDs. Coverage is partial: a channel requires a matching regional guide and current programme listings. The website shows the latest actual count. The full coverage report lists every missing channel ID. A name match does not establish that a local affiliate or foreign edition has the same schedule.

The reviewed mapping set includes 510 playlist IDs, using Open-EPG and a public Xumo guide. Programme availability changes daily. NBC Comedy Vault, SNL Vault, and US Pluto TV Comedy are required for publication. Alternative sources fill schedule gaps; higher-priority sources win overlapping times. Duplicate channel definitions with identical names are coalesced. Conflicting definitions for mapped IDs fail the build.

## Updates and maintenance

GitHub Actions runs daily at 20:37 UTC (22:37 Malta summer time, 21:37 winter time), after Open-EPG's suggested evening refresh. Scheduled runs can be delayed by GitHub. The configuration uses 18 Open-EPG files per daily run, below its stated 20-file daily limit, plus one Xumo guide. Avoid repeated manual downloads.

A failed download, invalid source, missing required channel, or coverage below 380 IDs stops publication and leaves the previous feed online. Check the website's update timestamp if listings become stale; source guides have a short future window. No feed can manufacture listings absent from its sources.

GitHub may disable scheduled workflows in public repositories after 60 days without repository activity. If that happens, open Actions > Refresh EPG and re-enable the workflow. Review the schedule and status periodically. No paid service or always-on computer is needed.

## Technical details

Python 3.12, standard library only. Handles plain XML and gzip by file signature, converts timestamps to UTC, filters stale listings, preserves playlist tvg-id values, and removes duplicate/overlapping programmes. Output is both XML and gzip; Pages deploys only after a successful build. Nine focused tests cover decoding, offsets, mapping, regional separation, source priority, duplicate channel definitions, and failure handling.

Source inventory and coverage reports are retained as workflow artifacts for seven days. The hosted coverage report is updated with each successful deployment. Manual channel mapping changes should be audited before publication. Do not put private source tokens in this public repository.

Sources: https://www.open-epg.com/app/epgguide.php and https://github.com/abusaeeidx/IPTV-Scraper-Zilla

