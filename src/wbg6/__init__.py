"""WBG-6: leaderboard-score inversion of the hidden DOE GEMS label distribution.

The competition truth (expert-labelled faults absent from the public catalogue) is
never released.  What we do have is 118 owner-reported scores, each of which is an
exact functional of that hidden truth.  This package turns those scores into a
fitted spatial prior for the truth, and from the prior into a submission.

Nothing here reproduces organizer labels, and no score produced here is an
organizer result: predicted scores are MODEL-ESTIMATE, never ORGANIZER-CONFIRMED.
"""
from .truth_model import (ALPHA, BETA, RADIUS_PX, RING_EDGES, ModelFit,
                          dti_components, dti_from_components, predict_score,
                          ring_ids, sufficient_statistics)

__all__ = ["ALPHA", "BETA", "RADIUS_PX", "RING_EDGES", "ModelFit",
           "dti_components", "dti_from_components", "predict_score",
           "ring_ids", "sufficient_statistics"]
