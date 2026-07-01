PARK_FACTORS = {
    "Coors Field": 1.18,
    "Great American Ball Park": 1.12,
    "Fenway Park": 1.08,
    "Yankee Stadium": 1.07,
    "Citizens Bank Park": 1.06,
    "Oriole Park at Camden Yards": 1.05,
    "Truist Park": 1.04,
    "Wrigley Field": 1.03,
    "Dodger Stadium": 1.02,
    "Minute Maid Park": 1.01,
    "Chase Field": 1.00,
    "Globe Life Field": 1.00,
    "Citi Field": 0.99,
    "Petco Park": 0.98,
    "Busch Stadium": 0.97,
    "American Family Field": 0.97,
    "T-Mobile Park": 0.94,
    "Oracle Park": 0.92,
    "Comerica Park": 0.91,
}


def get_park_factor(venue):
    return {
        "venue": venue,
        "run_factor": PARK_FACTORS.get(venue, 1.00),
        "source": "manual starter table"
    }