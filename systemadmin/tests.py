import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Criteria, Judge, Participant, Score


User = get_user_model()
DEFAULT_ADMIN_USERNAME = "tabulator_admin"
DEFAULT_ADMIN_PASSWORD = "tabulator123"


class AuthFlowTests(TestCase):
    def test_default_admin_account_exists(self):
        admin_user = User.objects.get(username=DEFAULT_ADMIN_USERNAME)

        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.check_password(DEFAULT_ADMIN_PASSWORD))

    def test_admin_login_redirects_to_admin_dashboard(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": DEFAULT_ADMIN_USERNAME,
                "password": DEFAULT_ADMIN_PASSWORD,
            },
        )

        self.assertRedirects(response, reverse("systemadmin:admin_dashboard"))

    def test_judge_login_redirects_to_judge_dashboard(self):
        judge_user = User.objects.create_user(username="judge_login", password="judgepass123")
        Judge.objects.create(user=judge_user)

        response = self.client.post(
            reverse("login"),
            {
                "username": "judge_login",
                "password": "judgepass123",
            },
        )

        self.assertRedirects(response, reverse("judge:judge_dashboard"))

    def test_anonymous_user_is_redirected_to_login_from_admin_dashboard(self):
        response = self.client.get(reverse("systemadmin:admin_dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_judge_user_is_redirected_away_from_admin_dashboard(self):
        judge_user = User.objects.create_user(username="judge_guard", password="judgepass123")
        Judge.objects.create(user=judge_user)
        self.client.force_login(judge_user)

        response = self.client.get(reverse("systemadmin:admin_dashboard"))

        self.assertRedirects(response, reverse("judge:judge_dashboard"))


class AdminAccessTestCase(TestCase):
    def setUp(self):
        self.admin_user = User.objects.get(username=DEFAULT_ADMIN_USERNAME)
        self.client.force_login(self.admin_user)


class CriteriaManagementTests(AdminAccessTestCase):
    def setUp(self):
        super().setUp()
        self.criteria = Criteria.objects.create(name="Talent", percentage=50)
        self.criteria_two = Criteria.objects.create(name="Poise", percentage=30)
        self.criteria_three = Criteria.objects.create(name="Q&A", percentage=20)

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
        judge_user = User.objects.create_user(username="judge1", password="secret123")
        judge = Judge.objects.create(user=judge_user)
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

    def test_admin_can_reorder_criteria(self):
        ordered_ids = [self.criteria_three.id, self.criteria.id, self.criteria_two.id]

        response = self.client.post(
            reverse("systemadmin:reorder_criteria"),
            data=json.dumps({"ordered_ids": ordered_ids}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"success": True})
        self.assertEqual(list(Criteria.objects.values_list("id", flat=True)), ordered_ids)

    def test_reorder_criteria_requires_full_saved_list(self):
        response = self.client.post(
            reverse("systemadmin:reorder_criteria"),
            data=json.dumps({"ordered_ids": [self.criteria.id, self.criteria_two.id]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            list(Criteria.objects.order_by("display_order", "id").values_list("id", flat=True)),
            [self.criteria.id, self.criteria_two.id, self.criteria_three.id],
        )


class ParticipantManagementTests(AdminAccessTestCase):
    def setUp(self):
        super().setUp()
        self.participant = Participant.objects.create(name="Contestant 1")

    def test_admin_can_edit_participant(self):
        response = self.client.post(
            reverse("systemadmin:edit_participant", args=[self.participant.id]),
            {
                "name": "Contestant Prime",
            },
        )

        self.assertRedirects(response, reverse("systemadmin:participant_list"))
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.name, "Contestant Prime")

    def test_admin_can_delete_participant_and_linked_scores(self):
        criteria = Criteria.objects.create(name="Talent", percentage=50)
        judge_user = User.objects.create_user(username="judge2", password="secret123")
        judge = Judge.objects.create(user=judge_user)
        Score.objects.create(
            judge=judge,
            participant=self.participant,
            criteria=criteria,
            score_value=88,
        )

        response = self.client.post(reverse("systemadmin:delete_participant", args=[self.participant.id]))

        self.assertRedirects(response, reverse("systemadmin:participant_list"))
        self.assertFalse(Participant.objects.filter(id=self.participant.id).exists())
        self.assertEqual(Score.objects.count(), 0)

    def test_delete_participant_requires_post(self):
        response = self.client.get(reverse("systemadmin:delete_participant", args=[self.participant.id]))

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Participant.objects.filter(id=self.participant.id).exists())


class JudgeAccountManagementTests(AdminAccessTestCase):
    def test_admin_can_create_judge_account(self):
        response = self.client.post(
            reverse("systemadmin:add_judge"),
            {
                "username": "judge_create",
                "password": "judgepass123",
                "confirm_password": "judgepass123",
            },
        )

        self.assertRedirects(response, reverse("systemadmin:judge_list"))
        judge = Judge.objects.get(user__username="judge_create")
        self.assertTrue(judge.user.check_password("judgepass123"))

    def test_admin_can_edit_judge_account(self):
        judge_user = User.objects.create_user(username="judge_edit", password="oldpass123")
        judge = Judge.objects.create(user=judge_user)

        response = self.client.post(
            reverse("systemadmin:edit_judge", args=[judge.id]),
            {
                "username": "judge_updated",
                "password": "newpass123",
                "confirm_password": "newpass123",
            },
        )

        self.assertRedirects(response, reverse("systemadmin:judge_list"))
        judge.refresh_from_db()
        self.assertEqual(judge.user.username, "judge_updated")
        self.assertTrue(judge.user.check_password("newpass123"))

    def test_admin_can_delete_judge_and_linked_scores(self):
        participant = Participant.objects.create(name="Contestant 3")
        criteria = Criteria.objects.create(name="Q&A", percentage=30)
        judge_user = User.objects.create_user(username="judge_delete", password="deletepass123")
        judge = Judge.objects.create(user=judge_user)
        Score.objects.create(
            judge=judge,
            participant=participant,
            criteria=criteria,
            score_value=90,
        )

        response = self.client.post(reverse("systemadmin:delete_judge", args=[judge.id]))

        self.assertRedirects(response, reverse("systemadmin:judge_list"))
        self.assertFalse(User.objects.filter(username="judge_delete").exists())
        self.assertFalse(Judge.objects.filter(id=judge.id).exists())
        self.assertEqual(Score.objects.count(), 0)

    def test_delete_judge_requires_post(self):
        judge_user = User.objects.create_user(username="judge_method", password="pass12345")
        judge = Judge.objects.create(user=judge_user)

        response = self.client.get(reverse("systemadmin:delete_judge", args=[judge.id]))

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Judge.objects.filter(id=judge.id).exists())


class JudgeScoringOrderTests(TestCase):
    def test_judge_sees_criteria_in_saved_display_order(self):
        first = Criteria.objects.create(name="Production", percentage=20)
        second = Criteria.objects.create(name="Talent", percentage=30)
        third = Criteria.objects.create(name="Q&A", percentage=50)

        first.display_order = 3
        first.save(update_fields=["display_order"])
        second.display_order = 1
        second.save(update_fields=["display_order"])
        third.display_order = 2
        third.save(update_fields=["display_order"])

        participant = Participant.objects.create(name="Contestant Ordered")
        judge_user = User.objects.create_user(username="judge_sequence", password="judgepass123")
        Judge.objects.create(user=judge_user)
        self.client.force_login(judge_user)

        response = self.client.get(reverse("judge:score_participant", args=[participant.id]))

        self.assertEqual(
            [criterion.id for criterion in response.context["criteria_list"]],
            [second.id, third.id, first.id],
        )
