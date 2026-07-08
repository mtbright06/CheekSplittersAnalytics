CSS = """
<style>
.stApp {
    background:
        radial-gradient(circle at top left, rgba(75, 110, 155, 0.35), transparent 35%),
        linear-gradient(135deg, #080d14 0%, #101827 45%, #06080d 100%);
    color: #f5f7fb;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1420 0%, #070a0f 100%);
    border-right: 1px solid rgba(124, 181, 255, 0.18);
}

div.stButton > button {
    border-radius: 999px;
    border: 1px solid rgba(160, 190, 230, 0.22);
    background: rgba(255,255,255,0.065);
    color: #d8e3f5;
    font-weight: 850;
    min-height: 42px;
}

div.stButton > button:hover {
    border-color: rgba(124, 181, 255, 0.60);
    background: rgba(65, 134, 255, 0.24);
    color: #ffffff;
}

.section-title {
    font-size: 28px;
    font-weight: 950;
    margin: 20px 0 12px 0;
    color: #f8fbff;
}

.reason {
    padding: 8px 10px;
    border-radius: 10px;
    background: rgba(255,255,255,0.045);
    margin-bottom: 8px;
    border-left: 3px solid #8ee6a3;
    color: #dce7f5;
    font-weight: 800;
}

/* Header / App Shell */

.app-header {
    position: relative;
    overflow: visible;
    padding: 22px 330px 18px 26px;
    min-height: 185px;
    border-radius: 24px;
    background:
        linear-gradient(135deg, rgba(25, 36, 54, 0.97), rgba(10, 14, 22, 0.97)),
        radial-gradient(circle at top right, rgba(113, 181, 255, 0.22), transparent 42%);
    border: 1px solid rgba(160, 190, 230, 0.20);
    box-shadow: 0 18px 55px rgba(0,0,0,0.42);
    margin-bottom: 16px;
}

.brand-row {
    display: flex;
    align-items: center;
    gap: 22px;
}

.logo-badge {
    width: 78px;
    height: 78px;
    border-radius: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    background:
        radial-gradient(circle at 30% 25%, #ffffff 0%, #d8e8ff 17%, transparent 18%),
        linear-gradient(145deg, #29486f, #101828);
    border: 1px solid rgba(255,255,255,0.20);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 10px 30px rgba(0,0,0,0.35);
    font-size: 34px;
}

.logo-img {
    width: 150px;
    height: auto;
    object-fit: contain;
    border: none;
    box-shadow: none;
    border-radius: 0;
}

.mascot-img {
    position: absolute;
    top: -34px;
    right: -8px;
    width: 420px;
    height: auto;
    z-index: 10;
    pointer-events: none;
    filter: drop-shadow(0 14px 28px rgba(0,0,0,.50));
}

.brand-title {
    font-size: 52px;
    font-weight: 1000;
    line-height: 0.95;
    letter-spacing: -1.8px;
    margin: 0;
    color: #f8fbff;
}

.brand-subtitle {
    color: #b9c7dc;
    font-size: 16px;
    font-weight: 750;
    margin-top: 6px;
}

.brand-tagline {
    display: inline-block;
    margin-top: 10px;
    padding: 7px 12px;
    border-radius: 999px;
    background: rgba(124, 181, 255, 0.10);
    border: 1px solid rgba(124, 181, 255, 0.24);
    color: #8ee6a3;
    font-weight: 900;
    font-size: 13px;
}

.logo-strip {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin: 22px 0 6px 0;
}

.sport-chip {
    padding: 8px 12px;
    border-radius: 14px;
    background: rgba(255,255,255,0.055);
    border: 1px solid rgba(160,190,230,0.14);
    font-weight: 900;
    color: #eaf1ff;
}

.version-chip {
    position: absolute;
    right: 26px;
    bottom: 18px;
    padding: 10px 14px;
    border-radius: 14px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.12);
    text-align: center;
    font-weight: 900;
    font-size: 13px;
    color: #d8e3f5;
    backdrop-filter: blur(8px);
}

.header-status-row {
    display: flex;
    gap: 10px;
    margin-top: 14px;
    flex-wrap: wrap;
}

.status-pill {
    padding: 7px 11px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 900;
}

.status-pill.good {
    background: rgba(40,140,70,0.28);
    color: #9cffb0;
}

.status-pill.warn {
    background: rgba(150,110,25,0.30);
    color: #ffd976;
}

.status-pill.off {
    background: rgba(255,255,255,0.08);
    color: #b7c2d8;
}

/* Shared Cards */

.sharp-card,
.placeholder-card,
.module-card,
.pipeline-card,
.engine-status-card {
    padding: 20px;
    border-radius: 20px;
    background: rgba(14, 21, 32, 0.92);
    border: 1px solid rgba(160, 190, 230, 0.14);
    box-shadow: 0 14px 36px rgba(0,0,0,0.28);
    margin-bottom: 18px;
}

.badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 900;
    letter-spacing: .4px;
    background: rgba(255,255,255,0.08);
    color: #ffffff;
    border: 1px solid rgba(255,255,255,0.14);
}

.badge-green {
    background: rgba(29, 97, 51, 0.45);
    color: #9cffb0;
    border-color: rgba(156,255,176,0.30);
}

.badge-gold {
    background: rgba(104, 78, 28, 0.45);
    color: #ffd976;
    border-color: rgba(255,217,118,0.30);
}

.badge-red {
    background: rgba(120, 45, 45, 0.45);
    color: #ffb0b0;
    border-color: rgba(255,120,120,0.30);
}

.muted {
    color: #aebbd0;
    font-size: 14px;
}

.small-label {
    color: #9dadc5;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    font-weight: 850;
}

.big-number {
    color: #8ee6a3;
    font-size: 42px;
    font-weight: 1000;
    line-height: 1;
}

.stMetric {
    background: rgba(255,255,255,0.035);
    padding: 10px;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.06);
}

/* Module Dashboard */

.module-hero {
    display: flex;
    align-items: center;
    gap: 22px;
    padding: 32px;
    border-radius: 26px;
    background:
        radial-gradient(circle at top right, rgba(124,181,255,.18), transparent 42%),
        linear-gradient(135deg,#152238,#090d14);
    border: 1px solid rgba(124,181,255,.22);
    box-shadow: 0 20px 60px rgba(0,0,0,.40);
    margin-bottom: 22px;
}

.module-icon {
    width: 86px;
    height: 86px;
    border-radius: 24px;
    background: rgba(255,255,255,.07);
    border: 1px solid rgba(255,255,255,.12);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 42px;
    flex-shrink: 0;
}

.module-title {
    font-size: 46px;
    font-weight: 1000;
    color: #fff;
    line-height: 1;
}

.module-subtitle {
    margin-top: 8px;
    font-size: 18px;
    color: #b9c7dc;
    font-weight: 750;
}

.module-badge {
    display: inline-block;
    margin-top: 16px;
    padding: 8px 14px;
    border-radius: 999px;
    background: rgba(124,181,255,.12);
    border: 1px solid rgba(124,181,255,.28);
    color: #d8e3f5;
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 1px;
}

.module-card-title {
    color: #f8fbff;
    font-size: 17px;
    font-weight: 1000;
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.module-row,
.pipeline-row,
.engine-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    color: #d8e3f5;
    font-size: 14px;
    font-weight: 850;
}

.module-row:last-child,
.pipeline-row:last-child,
.engine-row:last-child {
    border-bottom: none;
}

.module-row strong,
.pipeline-row strong,
.engine-row strong {
    text-align: right;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: .7px;
    font-weight: 1000;
}

.module-complete {
    color: #9cffb0;
}

.module-next {
    color: #ffd976;
}

.module-planned {
    color: #aebbd0;
}

/* Team / Matchup */

.team-title {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 16px;
    border-radius: 14px;
    background: rgba(255,255,255,0.035);
    font-size: 24px;
    font-weight: 900;
    color: #f8fbff;
}

.team-title span {
    font-size: 24px;
    font-weight: 900;
    color: #f8fbff;
}

.team-logo,
.team-logo-placeholder {
    width: 72px;
    height: 72px;
    min-width: 72px;
    min-height: 72px;
    object-fit: contain;
    flex-shrink: 0;
}

.team-logo-placeholder {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    font-size: 24px;
}

.matchup-title {
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
    font-size: 24px;
    font-weight: 950;
    color: #f8fbff;
}

.matchup-at {
    color: #9dadc5;
    font-size: 18px;
    font-weight: 900;
}

.matchup-hero {
    margin: 18px 0;
    padding: 18px;
    border-radius: 22px;
    background: linear-gradient(135deg, rgba(18,28,42,.95), rgba(8,12,18,.95));
    border: 1px solid rgba(160,190,230,.14);
}

.matchup-team-block {
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 18px;
    border-radius: 18px;
    background: rgba(255,255,255,.04);
}

.matchup-logo-wrap .team-logo,
.matchup-logo-wrap .team-logo-placeholder {
    width: 76px;
    height: 76px;
    min-width: 76px;
    min-height: 76px;
}

.matchup-side-label {
    color: #9dadc5;
    font-size: 12px;
    font-weight: 900;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.matchup-team-name {
    color: #f8fbff;
    font-size: 30px;
    font-weight: 1000;
    line-height: 1;
}

.matchup-vs {
    height: 100%;
    min-height: 108px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #9dadc5;
    font-size: 24px;
    font-weight: 1000;
}

/* Daily Lock / Core Picks */

.daily-lock-card {
    padding: 24px;
    border-radius: 24px;
    background:
        radial-gradient(circle at top right, rgba(142, 230, 163, 0.16), transparent 38%),
        linear-gradient(135deg, rgba(18, 28, 42, 0.96), rgba(8, 12, 18, 0.96));
    border: 1px solid rgba(142, 230, 163, 0.22);
    box-shadow: 0 18px 55px rgba(0,0,0,0.34);
    margin-bottom: 14px;
}

.daily-lock-layout {
    display: flex;
    align-items: center;
    gap: 24px;
}

.daily-lock-logo-wrap {
    width: 132px;
    height: 132px;
    min-width: 132px;
    min-height: 132px;
    border-radius: 28px;
    background: rgba(255,255,255,0.055);
    border: 1px solid rgba(255,255,255,0.10);
    display: flex;
    align-items: center;
    justify-content: center;
}

.daily-lock-logo-wrap .team-logo,
.daily-lock-logo-wrap .team-logo-placeholder {
    width: 108px;
    height: 108px;
    min-width: 108px;
    min-height: 108px;
}

.daily-lock-content {
    flex: 1;
}

.daily-lock-kicker {
    color: #9cffb0;
    font-size: 13px;
    font-weight: 1000;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 8px;
}

.daily-lock-title {
    color: #f8fbff;
    font-size: 42px;
    line-height: 1.02;
    font-weight: 1000;
    letter-spacing: -1px;
}

.daily-lock-subtitle {
    color: #aebbd0;
    margin-top: 8px;
    font-size: 15px;
    font-weight: 800;
}

.daily-lock-market {
    margin-top: 6px;
    color: #ffd976;
    font-size: 18px;
    font-weight: 950;
    text-transform: uppercase;
    letter-spacing: .8px;
}

.daily-lock-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-top: 18px;
}

.daily-lock-grid div {
    padding: 14px;
    border-radius: 16px;
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);
}

.daily-lock-grid span {
    display: block;
    color: #9dadc5;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 900;
}

.daily-lock-grid strong {
    display: block;
    margin-top: 6px;
    color: #8ee6a3;
    font-size: 26px;
    font-weight: 1000;
}

.compact-pick {
    display: grid;
    grid-template-columns: 72px 1fr auto;
    gap: 14px;
    align-items: center;
    padding: 14px;
    border-radius: 18px;
    background: rgba(14, 21, 32, 0.92);
    border: 1px solid rgba(160, 190, 230, 0.13);
    box-shadow: 0 10px 24px rgba(0,0,0,0.22);
    margin-bottom: 12px;
}

.compact-logo .team-logo,
.compact-logo .team-logo-placeholder {
    width: 58px;
    height: 58px;
    min-width: 58px;
    min-height: 58px;
}

.compact-title {
    color: #f8fbff;
    font-size: 24px;
    font-weight: 1000;
    line-height: 1;
}

.compact-subtitle {
    color: #aebbd0;
    font-size: 13px;
    font-weight: 800;
    margin: 5px 0 8px 0;
}

.compact-metrics {
    display: flex;
    gap: 10px;
}

.compact-metrics div {
    min-width: 74px;
    padding: 10px;
    border-radius: 13px;
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);
}

.compact-metrics span {
    display: block;
    color: #9dadc5;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 900;
}

.compact-metrics strong {
    display: block;
    color: #8ee6a3;
    margin-top: 4px;
    font-size: 18px;
    font-weight: 1000;
}

.play-hero {
    margin: 18px 0 10px 0;
    padding: 20px;
    border-radius: 18px;
    background:
        radial-gradient(circle at top right, rgba(142, 230, 163, 0.12), transparent 38%),
        linear-gradient(135deg, rgba(18, 28, 42, 0.94), rgba(9, 13, 20, 0.94));
    border: 1px solid rgba(142, 230, 163, 0.18);
    box-shadow: 0 14px 36px rgba(0,0,0,0.28);
    display: flex;
    justify-content: space-between;
    gap: 18px;
    align-items: center;
}

.play-title {
    font-size: 34px;
    line-height: 1.05;
    font-weight: 1000;
    color: #f8fbff;
    letter-spacing: -0.8px;
    margin-top: 5px;
}

.play-hero-footer {
    display: flex;
    gap: 12px;
    align-items: center;
    margin-bottom: 8px;
}

.play-hero-metrics {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    justify-content: flex-end;
}

.play-hero-metrics div {
    min-width: 112px;
    padding: 12px;
    border-radius: 14px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
}

.play-hero-metrics span {
    display: block;
    color: #9dadc5;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 900;
}

.play-hero-metrics strong {
    display: block;
    margin-top: 5px;
    color: #8ee6a3;
    font-size: 28px;
    font-weight: 1000;
}

.value-meter {
    margin: 12px 0;
    padding: 16px;
    border-radius: 18px;
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.07);
}

.value-title {
    color: #f8fbff;
    font-size: 15px;
    font-weight: 950;
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.value-row {
    display: grid;
    grid-template-columns: 120px 1fr 64px;
    align-items: center;
    gap: 12px;
    margin-bottom: 10px;
}

.value-label {
    color: #aebbd0;
    font-size: 13px;
    font-weight: 850;
}

.value-track {
    height: 10px;
    border-radius: 999px;
    background: rgba(255,255,255,0.08);
    overflow: hidden;
}

.value-fill {
    height: 100%;
    border-radius: 999px;
}

.book-fill {
    background: rgba(174,187,208,0.55);
}

.value-number {
    color: #d8e3f5;
    font-size: 13px;
    font-weight: 900;
    text-align: right;
}

.value-edge {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid rgba(255,255,255,0.08);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.value-edge span {
    color: #9dadc5;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 900;
}

.value-edge strong {
    font-size: 30px;
    font-weight: 1000;
}

.progress-wrap {
    margin: 14px 0;
    padding: 10px 12px;
    border-radius: 14px;
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.06);
}

.compact-progress {
    margin: 8px 0;
}

.progress-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #d8e3f5;
    font-size: 13px;
    font-weight: 850;
    margin-bottom: 8px;
}

.progress-track {
    width: 100%;
    height: 9px;
    border-radius: 999px;
    background: rgba(255,255,255,0.08);
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    border-radius: 999px;
}

.splitter-comment {
    margin: 12px 0 4px 0;
    padding: 12px 14px;
    border-radius: 14px;
    background: rgba(124, 181, 255, 0.08);
    border: 1px solid rgba(124, 181, 255, 0.18);
    color: #d8e3f5;
    font-weight: 850;
}

/* Bomb Lab V2 */

.bomb-v2-hero {
    display: grid;
    grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.8fr);
    gap: 18px;
    background:
        radial-gradient(circle at top right, rgba(255, 207, 112, 0.10), transparent 35%),
        linear-gradient(135deg, rgba(16, 24, 38, 0.98), rgba(8, 13, 22, 0.98));
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 22px;
    padding: 20px;
    margin: 14px 0 22px 0;
    box-shadow: 0 14px 28px rgba(0,0,0,0.25);
}

.bomb-v2-kicker {
    color: #ffcf70;
    font-size: 12px;
    font-weight: 1000;
    letter-spacing: 1.4px;
    text-transform: uppercase;
}

.bomb-v2-title {
    color: #f8fbff;
    font-size: 34px;
    font-weight: 1000;
    line-height: 1.05;
    margin-top: 4px;
}

.bomb-v2-copy {
    color: #aebbd0;
    font-size: 14px;
    font-weight: 750;
    line-height: 1.45;
    margin-top: 10px;
    max-width: 780px;
}

.bomb-v2-summary {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
}

.bomb-v2-summary div {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 16px;
    padding: 14px;
}

.bomb-v2-summary span {
    display: block;
    color: #9dadc5;
    font-size: 10px;
    font-weight: 1000;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.bomb-v2-summary strong {
    display: block;
    color: #f8fbff;
    font-size: 30px;
    font-weight: 1000;
    margin-top: 4px;
}

.decision-v2-card {
    display: grid;
    grid-template-columns: 50px minmax(260px, 1.3fr) minmax(260px, 1fr) minmax(210px, 0.8fr) minmax(280px, 1.2fr);
    gap: 14px;
    align-items: center;
    background: rgba(13, 20, 31, 0.96);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 18px;
    padding: 15px;
    margin: 13px 0;
    box-shadow: 0 12px 24px rgba(0,0,0,0.22);
}

.decision-v2-card:hover {
    border-color: rgba(255, 207, 112, 0.36);
    transform: translateY(-1px);
}

.decision-v2-rank {
    width: 42px;
    height: 42px;
    border-radius: 13px;
    background: linear-gradient(135deg, #ef4444, #f97316);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    font-weight: 1000;
}

.decision-v2-label {
    color: #ffcf70;
    font-size: 12px;
    font-weight: 1000;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.decision-v2-title {
    color: #f8fbff;
    font-size: 24px;
    font-weight: 1000;
    line-height: 1.05;
}

.decision-v2-subtitle {
    color: #aebbd0;
    font-size: 13px;
    font-weight: 800;
    margin-top: 4px;
}

.decision-v2-stars {
    color: #facc15;
    font-size: 15px;
    font-weight: 1000;
    margin-top: 6px;
    letter-spacing: 1px;
}

.decision-v2-metrics {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
}

.decision-v2-metrics div {
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 13px;
    padding: 9px;
}

.decision-v2-metrics span,
.decision-v2-small-label {
    display: block;
    color: #9dadc5;
    font-size: 10px;
    font-weight: 1000;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.decision-v2-metrics strong {
    display: block;
    color: #f8fbff;
    font-size: 17px;
    font-weight: 1000;
    margin-top: 4px;
}

.decision-v2-targets {
    display: grid;
    gap: 6px;
}

.decision-v2-targets span:not(.decision-v2-small-label) {
    color: #e8f3ff;
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 999px;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: 900;
}

.decision-v2-why ul {
    margin: 6px 0 0 0;
    padding-left: 18px;
}

.decision-v2-why li {
    color: #a7f3d0;
    font-size: 12px;
    font-weight: 800;
    line-height: 1.35;
    margin-bottom: 4px;
}

.game-v2-card {
    background: rgba(13, 20, 31, 0.96);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 22px;
    padding: 18px;
    margin-top: 12px;
    box-shadow: 0 12px 24px rgba(0,0,0,0.22);
}

.game-v2-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 18px;
}

.game-v2-title {
    color: #f8fbff;
    font-size: 38px;
    font-weight: 1000;
    line-height: 1.05;
}

.game-v2-subtitle {
    color: #aebbd0;
    font-size: 15px;
    font-weight: 800;
    margin-top: 6px;
}

.game-v2-score {
    min-width: 130px;
    text-align: center;
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 12px;
}

.game-v2-score span {
    color: #9dadc5;
    font-size: 10px;
    font-weight: 1000;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.game-v2-score strong {
    display: block;
    color: #ff7676;
    font-size: 44px;
    font-weight: 1000;
    line-height: 1;
    margin-top: 6px;
}

.game-v2-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-top: 16px;
}

.game-v2-grid div {
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 12px;
}

.game-v2-grid span {
    display: block;
    color: #9dadc5;
    font-size: 10px;
    font-weight: 1000;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.game-v2-grid strong {
    display: block;
    color: #f8fbff;
    font-size: 20px;
    font-weight: 1000;
    margin-top: 6px;
}

.target-hitter-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 12px 14px;
    margin: 8px 0;
}

.target-hitter-row strong {
    display: block;
    color: #f8fbff;
    font-size: 16px;
    font-weight: 1000;
}

.target-hitter-row span {
    display: block;
    color: #9dadc5;
    font-size: 12px;
    font-weight: 800;
    margin-top: 3px;
}

.target-score {
    color: #ffcf70;
    font-size: 24px;
    font-weight: 1000;
}

.metric-groups {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin-top: 16px;
}

.metric-group {
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 14px;
}

.metric-group h4 {
    margin: 0 0 10px 0;
    color: #f8fbff;
    font-size: 15px;
    font-weight: 1000;
}

.metric-group p {
    margin: 6px 0;
    color: #bfd0e6;
    font-size: 13px;
    font-weight: 800;
}

/* Bomb Lab Pitcher Explorer */

.bomb-card {
    background: rgba(14, 21, 32, 0.94);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 22px;
    padding: 18px;
    margin: 16px 0 8px 0;
    box-shadow: 0 12px 26px rgba(0,0,0,0.22);
}

.bomb-card.compact {
    padding: 14px;
    margin: 12px 0 6px 0;
}

.bomb-card-top {
    display: flex;
    justify-content: space-between;
    gap: 18px;
    align-items: flex-start;
}

.bomb-tier {
    color: #ffcf70;
    font-size: 13px;
    font-weight: 1000;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.bomb-title {
    color: #f8fbff;
    font-size: 24px;
    font-weight: 1000;
    line-height: 1.05;
}

.pitcher-team {
    color: #9dadc5;
    font-size: 18px;
    font-weight: 900;
}

.bomb-subtitle {
    color: #aebbd0;
    font-size: 14px;
    font-weight: 800;
    margin-top: 4px;
}

.bomb-score {
    min-width: 88px;
    text-align: center;
    color: #ff7676;
    font-size: 36px;
    font-weight: 1000;
    line-height: 1;
}

.bomb-grid,
.bomb-stats {
    display: grid;
    gap: 10px;
    margin-top: 14px;
}

.bomb-grid {
    grid-template-columns: repeat(4, 1fr);
}

.bomb-stats {
    grid-template-columns: repeat(5, 1fr);
}

.bomb-grid div,
.bomb-stats div {
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 10px;
}

.bomb-grid span,
.bomb-stats span {
    display: block;
    color: #9dadc5;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 900;
}

.bomb-grid strong,
.bomb-stats strong {
    display: block;
    color: #f8fbff;
    margin-top: 4px;
    font-size: 17px;
    font-weight: 1000;
}

/* Responsive */

@media (max-width: 1200px) {
    .decision-v2-card {
        grid-template-columns: 48px 1fr;
    }

    .decision-v2-metrics,
    .bomb-v2-summary,
    .game-v2-grid,
    .metric-groups,
    .bomb-v2-hero,
    .daily-lock-grid {
        grid-template-columns: 1fr;
    }

    .game-v2-header,
    .daily-lock-layout,
    .play-hero {
        flex-direction: column;
        align-items: stretch;
    }

    .app-header {
        padding-right: 26px;
    }

    .mascot-img {
        display: none;
    }
}

</style>
"""
