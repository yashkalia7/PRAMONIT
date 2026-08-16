"""Registration, login, role gates and the coach dropdown."""

from __future__ import annotations

from tests.conftest import API, auth_headers, register_coach, register_student


async def test_coach_registration_returns_tokens_and_profile(client):
    coach = await register_coach(client, full_name="Rahul Menon")
    assert coach["tokens"]["access_token"]
    assert coach["user"]["role"] == "coach"
    assert coach["user"]["coach_profile"]["primary_location"] == "Powai"


async def test_student_registration_links_to_the_chosen_coach(client):
    coach = await register_coach(client)
    student = await register_student(client, coach["user"]["id"], batch_name="Powai batch")

    profile = student["user"]["student_profile"]
    assert profile["coach_id"] == coach["user"]["id"]
    assert profile["coach_name"] == coach["user"]["full_name"]
    assert profile["batch_name"] == "Powai batch"
    # Active immediately — no waiting on the coach to accept.
    assert profile["roster_status"] == "active"


async def test_student_registration_captures_the_verbose_fields(client):
    coach = await register_coach(client)
    student = await register_student(
        client,
        coach["user"]["id"],
        jersey_number=10,
        preferred_position="Attacking midfielder",
        dominant_foot="left",
        height_cm=162,
        weight_kg=48.5,
        years_playing=4,
        previous_club="Powai Juniors",
        school_name="Bombay Scottish",
        guardian_name="Mrs. Mehta",
        guardian_phone="+91 9820011111",
        emergency_contact="+91 9820022222",
        medical_notes="Mild asthma — carries an inhaler",
        consent_media=True,
    )
    profile = student["user"]["student_profile"]
    assert profile["jersey_number"] == 10
    assert profile["dominant_foot"] == "left"
    assert profile["medical_notes"].startswith("Mild asthma")
    assert profile["consent_media"] is True


async def test_registering_against_an_unknown_coach_is_rejected(client):
    response = await client.post(
        f"{API}/auth/register/student",
        json={
            "email": "nobody@pramonit.dev",
            "password": "studentpass123",
            "full_name": "Ghost Player",
            "coach_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert response.status_code == 400


async def test_duplicate_email_is_a_conflict(client):
    coach = await register_coach(client)
    response = await client.post(
        f"{API}/auth/register/coach",
        json={"email": coach["email"], "password": "another123", "full_name": "Impostor"},
    )
    assert response.status_code == 409


async def test_email_is_case_insensitive(client):
    coach = await register_coach(client, email="Rahul.Menon@Pramonit.Dev")
    response = await client.post(
        f"{API}/auth/login",
        json={"email": "RAHUL.MENON@PRAMONIT.DEV", "password": coach["password"]},
    )
    assert response.status_code == 200


async def test_login_with_a_wrong_password_is_rejected(client):
    coach = await register_coach(client)
    response = await client.post(
        f"{API}/auth/login", json={"email": coach["email"], "password": "wrong-password"}
    )
    assert response.status_code == 401


async def test_login_does_not_reveal_whether_an_account_exists(client):
    coach = await register_coach(client)
    unknown = await client.post(
        f"{API}/auth/login", json={"email": "nobody@pramonit.dev", "password": "whatever123"}
    )
    wrong_pw = await client.post(
        f"{API}/auth/login", json={"email": coach["email"], "password": "whatever123"}
    )
    assert unknown.status_code == wrong_pw.status_code == 401
    assert unknown.json()["detail"] == wrong_pw.json()["detail"]


async def test_short_password_is_rejected(client):
    response = await client.post(
        f"{API}/auth/register/coach",
        json={"email": "x@pramonit.dev", "password": "short", "full_name": "Too Short"},
    )
    assert response.status_code == 422


async def test_me_requires_a_token(client):
    assert (await client.get(f"{API}/auth/me")).status_code == 401


async def test_refresh_token_cannot_be_used_as_an_access_token(client):
    """Otherwise a 30-day credential would authorise every ordinary request."""
    coach = await register_coach(client)
    refresh = coach["tokens"]["refresh_token"]
    response = await client.get(
        f"{API}/auth/me", headers={"Authorization": f"Bearer {refresh}"}
    )
    assert response.status_code == 401


async def test_refresh_endpoint_issues_a_new_access_token(client):
    coach = await register_coach(client)
    response = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": coach["tokens"]["refresh_token"]}
    )
    assert response.status_code == 200
    new_access = response.json()["access_token"]
    me = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200


async def test_garbage_token_is_rejected(client):
    response = await client.get(
        f"{API}/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"}
    )
    assert response.status_code == 401


async def test_public_coach_list_is_open_and_shows_roster_size(client):
    coach = await register_coach(client, full_name="Neha Kulkarni")
    await register_student(client, coach["user"]["id"])
    await register_student(client, coach["user"]["id"])

    response = await client.get(f"{API}/public/coaches")
    assert response.status_code == 200

    entry = next(c for c in response.json() if c["id"] == coach["user"]["id"])
    assert entry["full_name"] == "Neha Kulkarni"
    assert entry["student_count"] == 2
    assert entry["batches"] == ["Powai batch"]
    # A signup screen has no business seeing contact details.
    assert "email" not in entry
    assert "phone" not in entry


async def test_role_gates_are_enforced_in_both_directions(client):
    coach = await register_coach(client)
    student = await register_student(client, coach["user"]["id"])

    assert (
        await client.get(f"{API}/submissions/queue", headers=auth_headers(student))
    ).status_code == 403
    assert (
        await client.get(f"{API}/me/streak", headers=auth_headers(coach))
    ).status_code == 403
    assert (
        await client.get(f"{API}/coach/roster", headers=auth_headers(student))
    ).status_code == 403
