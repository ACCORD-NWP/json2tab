"""Module for merge strategy for manage merging of locations."""

from enum import Enum


class MergeStrategy(Enum):
    """Merge strategy used in location merger / windfarm turbine merger."""

    """ Combine data from both sources. """
    Combine = 0

    """ Use locations from first source and enrich it with data from second source. """
    EnrichSet1 = 1

    """ Use locations from second source and enrich it with data from first source. """
    EnrichSet2 = 2

    """ Intersect data from both sources. """
    Intersect = 3

    @staticmethod
    def from_string(value: str):
        """Converts a string to a MergeStrategy."""
        if value.upper() in ["COMBINE", "UNION", "OR"]:
            return MergeStrategy.Combine

        if value.upper() in [
            "ENRICHSET1",
            "ENRICH_SET_1",
            "ENRICH_1",
            "ENRICH_FIRST",
            "ENRICH1",
            "UNION_WITH_INTERSECTION_2",
        ]:
            return MergeStrategy.EnrichSet1

        if value.upper() in [
            "ENRICHSET2",
            "ENRICH_SET_2",
            "ENRICH_2",
            "ENRICH_SECOND",
            "ENRICH2",
            "UNION_WITH_INTERSECTION_1",
        ]:
            return MergeStrategy.EnrichSet2

        if value.upper() in [
            "COMMON",
            "INTERSECT",
            "AND",
        ]:
            return MergeStrategy.Intersect

        return None
