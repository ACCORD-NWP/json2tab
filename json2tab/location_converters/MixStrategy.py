"""Module for mix strategy for manage merging of locations."""

from enum import Enum

from ..location_converters.MergeStrategy import MergeStrategy


class MixStrategy(Enum):
    """Mix strategy used in location merger."""

    """ Merge all turbines from second source to one turbine to merge with. """
    MultiMerge = 0

    """ Merge only with the shortest distance turbine from second source. """
    SkipRemainder = 1

    """ Merge turbine from first source to all turbines from second source. """
    OuterJoin = 2

    """ Merge turbines only when there is a 1-to-1 relation; raise error otherwise. """
    Crash = 3

    @staticmethod
    def from_string(value: str):
        """Converts a string to a MixStrategy."""
        if value.upper() in ["MULTIMERGE", "MULTI_MERGE"]:
            return MixStrategy.MultiMerge

        if value.upper() in [
            "SKIPREMAINDER",
            "SKIP_REMAINDER",
        ]:
            return MixStrategy.SkipRemainder

        if value.upper() in [
            "OUTERJOIN",
            "OUTER_JOIN",
        ]:
            return MixStrategy.OuterJoin

        if value.upper() in [
            "CRASH",
            "ERROR",
        ]:
            return MixStrategy.Crash

        return None

    @staticmethod
    def from_merge_strategy(merge_strategy: MergeStrategy):
        """Derive MixStrategy from MergeStrategy."""
        if merge_strategy in [
            MergeStrategy.Combine,
            MergeStrategy.Intersect,
            MergeStrategy.EnrichSet1,
        ]:
            return MixStrategy.MultiMerge

        if merge_strategy in [MergeStrategy.EnrichSet2]:
            return MixStrategy.OuterJoin

        return None
