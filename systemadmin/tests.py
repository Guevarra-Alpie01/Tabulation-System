from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Criteria, Judge, Participant, Score


class CriteriaManagementTests(TestCase):
    def setUp(self):
        self.criteria = Criteria.objects.create(name="Talent", percentage=50)

    def test_admin_can_edit_criteria(self):
        response = self.client.post(
            reverse("systemadmin:edit_criteria", args=[self.criteria.id]),
            {
                "name": "Stage Presence",
                "percentage": "35",
            },
        )

        self.assertRedirects(response, reverse("systemadmin:criteria_list"))
        self.criteria.refresh_from_db()
        self.assertEqual(self.criteria.name, "Stage Presence")
        self.assertEqual(self.criteria.percentage, 35)

    def test_admin_can_delete_criteria_and_linked_scores(self):
        participant = Participant.objects.create(name="Contestant 1")
        user = User.objects.create_user(username="judge1", password="secret123")
        judge = Judge.objects.create(user=user)
        Score.objects.create(
            judge=judge,
            participant=participant,
            criteria=self.criteria,
            score_value=92,
        )

        response = self.client.post(reverse("systemadmin:delete_criteria", args=[self.criteria.id]))

        self.assertRedirects(response, reverse("systemadmin:criteria_list"))
        self.assertFalse(Criteria.objects.filter(id=self.criteria.id).exists())
        self.assertEqual(Score.objects.count(), 0)

    def test_delete_criteria_requires_post(self):
        response = self.client.get(reverse("systemadmin:delete_criteria", args=[self.criteria.id]))

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Criteria.objects.filter(id=self.criteria.id).exists())
