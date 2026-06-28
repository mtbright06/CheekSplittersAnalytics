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
    padding: 22px 26px 18px 26px;
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
    gap: 18px;
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
    width: 78px;
    height: 78px;
    object-fit: cover;
    border-radius: 22px;
    border: 1px solid rgba(255,255,255,0.20);
    box-shadow: 0 10px 30px rgba(0,0,0,0.35);
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

.logo-strip {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin: 12px 0 6px 0;
}

.sport-chip {
    padding: 8px 12px;
    border-radius: 14px;
    background: rgba(255,255,255,0.055);
    border: 1px solid rgba(160,190,230,0.14);
    font-weight: 900;
    color: #eaf1ff;
}

.stMetric {
    background: rgba(255,255,255,0.035);
    padding: 10px;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.06);
}
</style>
"""
