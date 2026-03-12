import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Criteria, Judge, LiveCriteriaSession, LiveCriteriaSubmission, Participant, Score


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

    def test_admin_cannot_raise_criteria_total_above_100_percent(self):
        response = self.client.post(
            reverse("systemadmin:add_criteria"),
            {
                "name": "Production Value",
                "percentage": "5",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The total criteria weight cannot exceed 100%")
        self.assertFalse(Criteria.objects.filter(name="Production Value").exists())


class ParticipantManagementTests(AdminAccessTestCase):
    def setUp(self):
        super().setUp()
        self.participant = Participant.objects.create(name="Contestant 1")
        self.participant_two = Participant.objects.create(name="Contestant 2")
        self.participant_three = Participant.objects.create(name="Contestant 3")

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
        self.participant_two.refresh_from_db()
        self.participant_three.refresh_from_db()
        self.assertEqual(self.participant_two.display_order, 1)
        self.assertEqual(self.participant_three.display_order, 2)

    def test_delete_participant_requires_post(self):
        response = self.client.get(reverse("systemadmin:delete_participant", args=[self.participant.id]))

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Participant.objects.filter(id=self.participant.id).exists())

    def test_admin_can_reorder_participants(self):
        ordered_ids = [self.participant_three.id, self.participant.id, self.participant_two.id]

        response = self.client.post(
            reverse("systemadmin:reorder_participants"),
            data=json.dumps({"ordered_ids": ordered_ids}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"success": True})
        self.assertEqual(list(Participant.objects.values_list("id", flat=True)), ordered_ids)

    def test_reorder_participants_requires_full_saved_list(self):
        response = self.client.post(
            reverse("systemadmin:reorder_participants"),
            data=json.dumps({"ordered_ids": [self.participant.id, self.participant_two.id]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            list(Participant.objects.order_by("display_order", "id").values_list("id", flat=True)),
            [self.participant.id, self.participant_two.id, self.participant_three.id],
        )


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


class LiveBroadcastWorkflowTests(AdminAccessTestCase):
    def setUp(self):
        super().setUp()
        self.production = Criteria.objects.create(name="Production", percentage=60)
        self.talent = Criteria.objects.create(name="Talent", percentage=40)
        self.participant_one = Participant.objects.create(name="Contestant 1")
        self.participant_two = Participant.objects.create(name="Contestant 2")
        judge_user = User.objects.create_user(username="judge_live", password="judgepass123")
        self.judge = Judge.objects.create(user=judge_user)
        second_user = User.objects.create_user(username="judge_pending", password="judgepass123")
        self.second_judge = Judge.objects.create(user=second_user)

    def test_admin_can_activate_live_criterion(self):
        response = self.client.post(reverse("systemadmin:activate_live_criterion", args=[self.production.id]))

        self.assertRedirects(response, reverse("systemadmin:admin_dashboard"))
        active_session = LiveCriteriaSession.objects.get(is_active=True)
        self.assertEqual(active_session.criterion, self.production)
        self.assertEqual(active_session.activated_by, self.admin_user)

    def test_activating_new_live_criterion_closes_previous_session(self):
        first_session = LiveCriteriaSession.objects.create(
            criterion=self.production,
            activated_by=self.admin_user,
            is_active=True,
        )

        response = self.client.post(reverse("systemadmin:activate_live_criterion", args=[self.talent.id]))

        self.assertRedirects(response, reverse("systemadmin:admin_dashboard"))
        first_session.refresh_from_db()
        self.assertFalse(first_session.is_active)
        self.assertIsNotNone(first_session.ended_at)
        self.assertTrue(LiveCriteriaSession.objects.filter(criterion=self.talent, is_active=True).exists())

    def test_live_activation_requires_criteria_total_of_100_percent(self):
        self.talent.percentage = 20
        self.talent.save(update_fields=["percentage"])

        response = self.client.post(reverse("systemadmin:activate_live_criterion", args=[self.production.id]))

        self.assertRedirects(response, reverse("systemadmin:admin_dashboard"))
        self.assertFalse(LiveCriteriaSession.objects.filter(is_active=True).exists())

    def test_judge_dashboard_shows_active_live_criterion(self):
        session = LiveCriteriaSession.objects.create(
            criterion=self.production,
            activated_by=self.admin_user,
            is_active=True,
        )
        self.client.force_login(self.judge.user)

        response = self.client.get(reverse("judge:judge_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_live_session"], session)
        self.assertEqual(len(response.context["live_score_rows"]), 2)

    def test_judge_dashboard_uses_saved_participant_order(self):
        session = LiveCriteriaSession.objects.create(
            criterion=self.production,
            activated_by=self.admin_user,
            is_active=True,
        )
        self.participant_one.display_order = 2
        self.participant_one.save(update_fields=["display_order"])
        self.participant_two.display_order = 1
        self.participant_two.save(update_fields=["display_order"])
        self.client.force_login(self.judge.user)

        response = self.client.get(reverse("judge:judge_dashboard"))

        self.assertEqual(response.context["active_live_session"], session)
        self.assertEqual(
            [row["participant"].id for row in response.context["live_score_rows"]],
            [self.participant_two.id, self.participant_one.id],
        )

    def test_judge_can_submit_live_scores_for_all_participants(self):
        session = LiveCriteriaSession.objects.create(
            criterion=self.production,
            activated_by=self.admin_user,
            is_active=True,
        )
        self.client.force_login(self.judge.user)

        response = self.client.post(
            reverse("judge:submit_live_scores"),
            {
                "live_session_id": str(session.id),
                f"participant_{self.participant_one.id}": "92",
                f"participant_{self.participant_two.id}": "87",
            },
        )

        self.assertRedirects(response, reverse("judge:judge_dashboard"))
        self.assertTrue(
            LiveCriteriaSubmission.objects.filter(session=session, judge=self.judge).exists()
        )
        self.assertEqual(
            Score.objects.get(judge=self.judge, participant=self.participant_one, criteria=self.production).score_value,
            92,
        )
        self.assertEqual(
            Score.objects.get(judge=self.judge, participant=self.participant_two, criteria=self.production).score_value,
            87,
        )

    def test_judge_live_submission_requires_score_for_every_participant(self):
        session = LiveCriteriaSession.objects.create(
            criterion=self.production,
            activated_by=self.admin_user,
            is_active=True,
        )
        self.client.force_login(self.judge.user)

        response = self.client.post(
            reverse("judge:submit_live_scores"),
            {
                "live_session_id": str(session.id),
                f"participant_{self.participant_one.id}": "92",
                f"participant_{self.participant_two.id}": "",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Enter a score for Contestant 2.", status_code=400)
        self.assertFalse(LiveCriteriaSubmission.objects.filter(session=session, judge=self.judge).exists())
        self.assertFalse(Score.objects.filter(judge=self.judge, criteria=self.production).exists())

    def test_live_status_reports_current_session_and_submission_state(self):
        session = LiveCriteriaSession.objects.create(
            criterion=self.production,
            activated_by=self.admin_user,
            is_active=True,
        )
        LiveCriteriaSubmission.objects.create(session=session, judge=self.judge)
        self.client.force_login(self.judge.user)

        response = self.client.get(reverse("judge:live_status"))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {
                "active_session_id": session.id,
                "criterion_name": "Production",
                "judge_has_submitted": True,
            },
        )


class WeightedResultsCalculationTests(AdminAccessTestCase):
    def test_results_average_judge_scores_before_applying_weights(self):
        talent = Criteria.objects.create(name="Talent", percentage=40)
        poise = Criteria.objects.create(name="Poise", percentage=60)
        contestant_a = Participant.objects.create(name="Contestant A")
        contestant_b = Participant.objects.create(name="Contestant B")
        judge_one = Judge.objects.create(user=User.objects.create_user(username="judge_avg_1", password="pass12345"))
        judge_two = Judge.objects.create(user=User.objects.create_user(username="judge_avg_2", password="pass12345"))

        Score.objects.create(judge=judge_one, participant=contestant_a, criteria=talent, score_value=80)
        Score.objects.create(judge=judge_two, participant=contestant_a, criteria=talent, score_value=100)
        Score.objects.create(judge=judge_one, participant=contestant_a, criteria=poise, score_value=70)
        Score.objects.create(judge=judge_two, participant=contestant_a, criteria=poise, score_value=90)

        Score.objects.create(judge=judge_one, participant=contestant_b, criteria=talent, score_value=90)
        Score.objects.create(judge=judge_two, participant=contestant_b, criteria=talent, score_value=80)
        Score.objects.create(judge=judge_one, participant=contestant_b, criteria=poise, score_value=60)
        Score.objects.create(judge=judge_two, participant=contestant_b, criteria=poise, score_value=70)

        response = self.client.get(reverse("systemadmin:results_data"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["results"],
            [
                {
                    "name": "Contestant A",
                    "photo_url": "",
                    "score": 84.0,
                    "criteria_scored": 2,
                    "judge_score_count": 4,
                },
                {
                    "name": "Contestant B",
                    "photo_url": "",
                    "score": 73.0,
                    "criteria_scored": 2,
                    "judge_score_count": 4,
                },
            ],
        )
        self.assertEqual(contestant_a.final_score(), 84.0)

    def test_results_page_includes_per_criterion_breakdown_tables(self):
        production = Criteria.objects.create(name="Production", percentage=20)
        talent = Criteria.objects.create(name="Talent", percentage=80)
        contestant_a = Participant.objects.create(name="Contestant A")
        contestant_b = Participant.objects.create(name="Contestant B")
        judge_one = Judge.objects.create(
            user=User.objects.create_user(username="judge_segment_1", password="pass12345")
        )
        judge_two = Judge.objects.create(
            user=User.objects.create_user(username="judge_segment_2", password="pass12345")
        )
        judge_three = Judge.objects.create(
            user=User.objects.create_user(username="judge_segment_3", password="pass12345")
        )

        Score.objects.create(judge=judge_one, participant=contestant_a, criteria=production, score_value=90)
        Score.objects.create(judge=judge_two, participant=contestant_a, criteria=production, score_value=95)
        Score.objects.create(judge=judge_three, participant=contestant_a, criteria=production, score_value=85)
        Score.objects.create(judge=judge_one, participant=contestant_b, criteria=production, score_value=80)
        Score.objects.create(judge=judge_two, participant=contestant_b, criteria=production, score_value=84)
        Score.objects.create(judge=judge_three, participant=contestant_b, criteria=production, score_value=86)

        Score.objects.create(judge=judge_one, participant=contestant_a, criteria=talent, score_value=92)
        Score.objects.create(judge=judge_two, participant=contestant_a, criteria=talent, score_value=90)
        Score.objects.create(judge=judge_three, participant=contestant_a, criteria=talent, score_value=88)
        Score.objects.create(judge=judge_one, participant=contestant_b, criteria=talent, score_value=89)
        Score.objects.create(judge=judge_two, participant=contestant_b, criteria=talent, score_value=87)
        Score.objects.create(judge=judge_three, participant=contestant_b, criteria=talent, score_value=85)

        response = self.client.get(reverse("systemadmin:tabulation_results"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [judge.user.username for judge in response.context["results_judges"]],
            ["judge_segment_1", "judge_segment_2", "judge_segment_3"],
        )

        breakdowns = response.context["criterion_breakdowns"]
        self.assertEqual([item["criterion"].id for item in breakdowns], [production.id, talent.id])

        production_rows = breakdowns[0]["rows"]
        self.assertEqual(production_rows[0]["participant"], contestant_a)
        self.assertEqual(production_rows[0]["judge_scores"], [90, 95, 85])
        self.assertEqual(production_rows[0]["submitted_count"], 3)
        self.assertEqual(production_rows[0]["average_score"], 90.0)
        self.assertEqual(production_rows[0]["weighted_score"], 18.0)
        self.assertEqual(production_rows[0]["rank"], 1)

        self.assertEqual(production_rows[1]["participant"], contestant_b)
        self.assertEqual(production_rows[1]["judge_scores"], [80, 84, 86])
        self.assertEqual(production_rows[1]["submitted_count"], 3)
        self.assertAlmostEqual(production_rows[1]["average_score"], 83.33, places=2)
        self.assertAlmostEqual(production_rows[1]["weighted_score"], 16.67, places=2)
        self.assertEqual(production_rows[1]["rank"], 2)

        self.assertEqual(breakdowns[0]["top_row"]["participant"], contestant_a)
        self.assertContains(response, "Criterion score tables")
        self.assertContains(response, "Weight 20.00%")
        self.assertContains(response, "judge_segment_1")
