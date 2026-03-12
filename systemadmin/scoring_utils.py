from django.db import connection

from .models import Criteria, Judge, LiveCriteriaSession, Participant


def acquire_scoring_write_lock():
    """
    Serialize writes that affect the live scoring state.

    On databases that support row-level locking, this locks a stable existing
    row from the scoring domain so concurrent admin/judge actions cannot create
    duplicate live sessions or conflicting score refreshes.
    """

    querysets = (
        Criteria.objects.order_by("id"),
        Participant.objects.order_by("id"),
        Judge.objects.order_by("id"),
        LiveCriteriaSession.objects.order_by("id"),
    )

    for queryset in querysets:
        if connection.features.has_select_for_update:
            anchor = queryset.select_for_update().first()
        else:
            anchor = queryset.first()

        if anchor is not None:
            return anchor

    return None
