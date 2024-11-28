import os
from json2table import convert
from controllers.utils import notify
from quicksand.quicksand import quicksand

def midstAnalysis(feedback):
    rating = feedback.get("rating", None)
    score = feedback.get("score", None)
    risk = feedback.get("risk", None)
    if not ((rating == 0) and (score == 0) and (risk == "nothing detected")):
        exploit = feedback.get("exploit")
        execute = feedback.get("execute")
        feature = feedback.get("feature")
        warning = feedback.get("warning")
        more_infos = feedback.get("results").get("root")[0]
        return f"""<b>**** QUICKSAND ENGINE RESULTS ***</b><br/>Below is the QuickSand analysis results : {convert(feedback)}"""

def analysis(FILE_PATH):
    if not os.path.isdir(FILE_PATH):
        qs2 = quicksand(FILE_PATH)
        try:
            qs2.process()
            feedback = qs2.results
            return midstAnalysis(feedback)
        except:
            pass