TEAM_COLORS = {

    # KBO

    "LG Twins": "#C3042F",

    "Samsung Lions": "#0066CC",

    "Doosan Bears": "#131230",

    "Lotte Giants": "#041E42",

    "Hanwha Eagles": "#F37321",

    "KIA Tigers": "#EA0029",

    "KT Wiz": "#000000",

    "NC Dinos": "#315288",

    "Kiwoom Heroes": "#570514",

    "SSG Landers": "#CE0E2D",



    # placeholders for MLB later

}


def team_color(team):

    return TEAM_COLORS.get(team, "#4b6e9b")
