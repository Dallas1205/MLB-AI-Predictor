def confidence_grade(score):
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def build_confidence_summary(quality):
    score = quality["score"]
    grade = confidence_grade(score)

    text = "\nPrediction Confidence\n"
    text += "---------------------\n"
    text += f"Score: {score}/100\n"
    text += f"Grade: {grade}\n"

    if quality["notes"]:
        text += "\nWhy score is lower:\n"
        for note in quality["notes"]:
            text += f"- {note}\n"

    return text