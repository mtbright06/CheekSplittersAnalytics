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

.app-header {
    position: relative;
    overflow: visible;
    padding: 22px 330px 18px 26px;
    min-height: 225px;
    border-radius: 24px;
    background:
        linear-gradient(135deg, rgba(25, 36, 54, 0.97), rgba(10, 14, 22, 0.97)),
        radial-gradient(circle at top right, rgba(113, 181, 255, 0.22), transparent 42%);
    border: 1px solid rgba(160, 190, 230, 0.20);
    box-shadow: 0 18px 55px rgba(0,0,0,0.42);
    margin-bottom: 16px;
    min-height: 185px;
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

.section-title {
    font-size: 28px;
    font-weight: 950;
    margin: 20px 0 12px 0;
    color: #f8fbff;
}

.sharp-card, .placeholder-card {
    padding: 22px;
    border-radius: 20px;
    background: rgba(14, 21, 32, 0.90);
    border: 1px solid rgba(160, 190, 230, 0.13);
    box-shadow: 0 14px 36px rgba(0,0,0,0.30);
    margin-bottom: 18px;
}

.best-card {
    padding: 26px;
    border-radius: 22px;
    background:
        linear-gradient(135deg, rgba(16, 24, 36, 0.98), rgba(25, 45, 75, 0.94)),
        radial-gradient(circle at top right, rgba(117, 210, 255, 0.20), transparent 38%);
    border: 1px solid rgba(124, 181, 255, 0.32);
    box-shadow: 0 18px 60px rgba(0,0,0,0.40);
    margin-bottom: 24px;
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

.reason {
    padding: 8px 10px;
    border-radius: 10px;
    background: rgba(255,255,255,0.045);
    margin-bottom: 8px;
    border-left: 3px solid #8ee6a3;
}

.signal-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 10px;
    border-radius: 10px;
    background: rgba(255,255,255,0.045);
    margin-bottom: 8px;
}

.pitcher-box {
    padding: 14px;
    border-radius: 14px;
    background: rgba(0,0,0,0.22);
    border: 1px solid rgba(160,190,230,0.10);
    min-height: 112px;
    margin-bottom: 10px;
}

.pitcher-name {
    font-size: 19px;
    font-weight: 950;
    color: #ffffff;
    margin-bottom: 4px;
}

.pitcher-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    margin-top: 12px;
}

.mini-tag {
    display: inline-block;
    padding: 5px 9px;
    border-radius: 999px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.10);
    color: #d8e3f5;
    font-size: 12px;
    font-weight: 850;
}

.mini-good {
    background: rgba(29, 97, 51, 0.42);
    border-color: rgba(156,255,176,0.28);
    color: #9cffb0;
}

.mini-bad {
    background: rgba(120, 45, 45, 0.42);
    border-color: rgba(255,120,120,0.28);
    color: #ffb0b0;
}

.feature-card {
    min-height: 155px;
    padding: 18px;
    border-radius: 18px;
    background:
        linear-gradient(135deg, rgba(18, 28, 42, 0.92), rgba(9, 13, 20, 0.92));
    border: 1px solid rgba(160, 190, 230, 0.13);
    box-shadow: 0 12px 30px rgba(0,0,0,0.25);
    margin-bottom: 16px;
}

.feature-icon {
    font-size: 30px;
    margin-bottom: 10px;
}

.feature-title {
    font-size: 18px;
    font-weight: 950;
    color: #f8fbff;
    margin-bottom: 6px;
}

.feature-body {
    color: #aebbd0;
    font-size: 14px;
    line-height: 1.35;
}

.lab-hero {
    margin: 20px 0;
    padding: 26px;
    border-radius: 24px;
    background:
        radial-gradient(circle at top right, rgba(255, 214, 118, 0.16), transparent 36%),
        linear-gradient(135deg, rgba(28, 42, 63, 0.94), rgba(8, 12, 18, 0.94));
    border: 1px solid rgba(255, 214, 118, 0.22);
    box-shadow: 0 18px 55px rgba(0,0,0,0.34);
}

.lab-title {
    font-size: 38px;
    font-weight: 1000;
    color: #f8fbff;
    letter-spacing: -1px;
}

.lab-subtitle {
    margin-top: 8px;
    color: #b9c7dc;
    font-size: 16px;
    font-weight: 700;
}

.lab-badge {
    display: inline-block;
    margin-top: 14px;
    padding: 7px 13px;
    border-radius: 999px;
    background: rgba(255, 214, 118, 0.12);
    border: 1px solid rgba(255, 214, 118, 0.26);
    color: #ffd976;
    font-size: 13px;
    font-weight: 950;
}

.hof-card {
    margin: 20px 0;
    padding: 26px;
    border-radius: 24px;
    background:
        radial-gradient(circle at top right, rgba(142, 230, 163, 0.14), transparent 36%),
        linear-gradient(135deg, rgba(18, 35, 26, 0.94), rgba(8, 12, 18, 0.94));
    border: 1px solid rgba(142, 230, 163, 0.22);
    box-shadow: 0 18px 55px rgba(0,0,0,0.34);
}

.hof-title {
    color: #9dadc5;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    font-weight: 900;
}

.hof-big {
    margin-top: 8px;
    font-size: 34px;
    font-weight: 1000;
    color: #f8fbff;
}

.hof-muted {
    margin-top: 8px;
    color: #aebbd0;
    font-size: 15px;
}

.stMetric {
    background: rgba(255,255,255,0.035);
    padding: 10px;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.06);
}

.pitcher-grade {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.20);
    font-size: 13px;
    font-weight: 950;
    letter-spacing: .4px;
}

.pending-grade {
    background: rgba(255,255,255,0.07);
    border-color: rgba(255,255,255,0.16);
    color: #aebbd0;
}

.badge-red {
    background: rgba(120, 45, 45, 0.45);
    color: #ffb0b0;
    border-color: rgba(255,120,120,0.30);
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

.matchup-title {
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
    font-size: 24px;
    font-weight: 950;
    color: #f8fbff;
}

.team-title {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 16px;
    border-radius: 14px;
    background: rgba(255,255,255,.035);
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

.matchup-at {
    color: #9dadc5;
    font-size: 24px;
    font-weight: 900;
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

.play-hero-footer {
    display: flex;
    gap: 12px;
    align-items: center;
    margin-bottom: 8px;
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

.engine-status-card {
    padding: 16px;
    border-radius: 18px;
    background: rgba(14, 21, 32, 0.90);
    border: 1px solid rgba(160, 190, 230, 0.13);
    box-shadow: 0 14px 36px rgba(0,0,0,0.28);
    margin-top: 20px;
}

.engine-title {
    color: #f8fbff;
    font-size: 15px;
    font-weight: 950;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
}

.engine-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    color: #aebbd0;
    font-size: 13px;
    font-weight: 800;
}

.engine-row:last-child {
    border-bottom: none;
}

.engine-row strong {
    color: #f8fbff;
    font-weight: 950;
    text-align: right;
}

.team-title{

    display:flex;

    align-items:center;

    gap:16px;

    padding:12px 16px;

    border-radius:14px;

    background:rgba(255,255,255,.035);

    .matchup-at {
    color: #9dadc5;
    font-size: 18px;
    font-weight: 900;
}

.version-chip{

position:absolute;

right:26px;

bottom:18px;

padding:10px 14px;

border-radius:14px;

background:rgba(255,255,255,.05);

border:1px solid rgba(255,255,255,.12);

text-align:center;

font-weight:900;

font-size:13px;

color:#d8e3f5;

backdrop-filter:blur(8px);

}

.header-status-row{

display:flex;

gap:10px;

margin-top:14px;

flex-wrap:wrap;

}

.status-pill{

padding:7px 11px;

border-radius:999px;

font-size:12px;

font-weight:900;

}

.status-pill.good{

background:rgba(40,140,70,.28);

color:#9cffb0;

}

.status-pill.warn{

background:rgba(150,110,25,.30);

color:#ffd976;

}

.status-pill.off{

background:rgba(255,255,255,.08);

color:#b7c2d8;

}

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

.pipeline-card {
    padding: 18px;
    border-radius: 20px;
    background: rgba(14, 21, 32, 0.92);
    border: 1px solid rgba(160, 190, 230, 0.14);
    box-shadow: 0 14px 36px rgba(0,0,0,0.28);
    margin-bottom: 16px;
}

.pipeline-title {
    color: #f8fbff;
    font-size: 15px;
    font-weight: 1000;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 12px;
}

.pipeline-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 9px 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    color: #aebbd0;
    font-size: 13px;
    font-weight: 850;
}

.pipeline-row:last-child {
    border-bottom: none;
}

.pipeline-row strong {
    color: #f8fbff;
    text-align: right;
    font-weight: 1000;
}


</style>
"""
