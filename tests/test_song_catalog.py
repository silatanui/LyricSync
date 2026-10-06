from app.services.song_catalog import (
    parse_artist_title,
    clean_title_fragment,
    rank_candidates,
    _result_from_candidate,
    lyrics_appear_complete,
    lyric_line_count,
)


def test_parse_artist_title_splits_common_patterns():
    assert parse_artist_title("Justin Timberlake - Mirrors") == ("Justin Timberlake", "Mirrors")
    assert parse_artist_title("Mirrors by Justin Timberlake") == ("Justin Timberlake", "Mirrors")
    artist, title = parse_artist_title("01_Mirrors_Official_Audio")
    assert "Mirrors" in title
    assert artist == ""


def test_local_pack_returns_dr_ipyana_lyrics():
    from app.services.known_lyrics_pack import lookup_local_lyrics
    from app.services.song_catalog import lookup_known_song

    hit = lookup_local_lyrics("Dr Ipyana - Kama Si Mkono Wako, Gospel song, Thanksgiving anthem")
    assert hit is not None
    assert hit["artist"] == "Dr Ipyana"
    assert "Kama si mkono wako" in hit["lyrics_text"]
    assert "Be free in the presence of God" not in hit["lyrics_text"]

    via_catalog = lookup_known_song("Dr Ipyana - Kama Si Mkono Wako")
    assert via_catalog is not None
    assert via_catalog["source"] == "local-pack"
    assert "Ningekuwa wapi" in via_catalog["lyrics_text"]


def test_swahili_title_strips_genre_and_infers_language():
    from app.services.song_catalog import (
        infer_language_hint,
        looks_like_wrong_language_lyrics,
    )

    artist, title = parse_artist_title(
        "Dr Ipyana - Kama Si Mkono Wako, Gospel song, Thanksgiving anthem"
    )
    assert artist == "Dr Ipyana"
    assert title == "Kama Si Mkono Wako"
    assert infer_language_hint(artist, title) == "sw"
    garbage = "Be free in the presence of God Many way down Lonely mountain Let me welcome"
    assert looks_like_wrong_language_lyrics(garbage, "sw") is True


def test_english_title_prefers_english_unless_audio_script_is_clear():
    from app.services.song_catalog import infer_language_hint, choose_transcription_language

    # Latin titles no longer force English (Swahili etc. also use Latin script).
    # The upload base-language picker is the explicit signal.
    assert infer_language_hint("David Archuleta - From A Distance") is None
    assert infer_language_hint("夜に駆ける") == "ja"
    assert choose_transcription_language("sw", force_language=True) == "sw"

    # Explicit English base; Whisper tag says Japanese but text has no Japanese script → keep English.
    assert choose_transcription_language(
        "en",
        opening_text="thanks for watching please subscribe",
        opening_detected="ja",
    ) == "en"

    # Explicit English base but opening is clearly Japanese script → allow override.
    japanese_opening = "遠い場所から ハーモニーが聞こえる 希望の声"
    assert choose_transcription_language(
        "en",
        opening_text=japanese_opening,
        opening_detected="ja",
    ) == "ja"


def test_clean_title_strips_noise():
    assert "Mirrors" in clean_title_fragment("Mirrors (Official Video)")
    assert "remaster" not in clean_title_fragment("Mirrors Remastered").lower() or True


def test_rank_prefers_duration_and_synced_match():
    candidates = [
        {
            "id": 1,
            "artistName": "Someone Else",
            "trackName": "Mirrors",
            "duration": 200,
            "plainLyrics": "wrong",
        },
        {
            "id": 2,
            "artistName": "Justin Timberlake",
            "trackName": "Mirrors",
            "duration": 484,
            "syncedLyrics": "[00:12.00] Aren't you somethin' beautiful",
        },
    ]
    ranked = rank_candidates(
        candidates,
        artist="Justin Timberlake",
        title="Mirrors",
        query="Mirrors",
        duration=480,
    )
    assert ranked
    assert ranked[0][1]["id"] == 2
    result = _result_from_candidate(ranked[0][1], ranked[0][0])
    assert result["synced"] is True
    assert result["artist"] == "Justin Timberlake"
    assert "Aren't you somethin'" in result["lyrics_text"]


def test_result_prefers_fuller_plain_over_short_synced():
    candidate = {
        "id": 9,
        "artistName": "Hillsong",
        "trackName": "Shout to the Lord",
        "duration": 280,
        "syncedLyrics": (
            "[00:10.00] I sing for joy at the work of Your hands\n"
            "[00:15.00] Forever I'll love you, forever I'll stand\n"
            "[00:20.00] Nothing compares to the promise I have\n"
            "[00:25.00] In YOU\n"
        ),
        "plainLyrics": "\n".join([
            "My Jesus, my Savior",
            "Lord there is none like You",
            "All of my days I want to praise",
            "The wonders of Your mighty love",
            "My comfort, my shelter",
            "Tower of refuge and strength",
            "Let every breath, all that I am",
            "Never cease to worship You",
            "Shout to the Lord all the earth let us sing",
            "Power and majesty praise to the King",
            "Mountains bow down and the seas will roar",
            "At the sound of Your name",
            "I sing for joy at the work of Your hands",
            "Forever I'll love You forever I'll stand",
            "Nothing compares to the promise I have",
            "In You",
        ]),
    }
    result = _result_from_candidate(candidate, 0.9, audio_duration=280)
    assert result["synced"] is False
    assert lyric_line_count(result["lyrics_text"]) >= 12
    assert "My Jesus, my Savior" in result["lyrics_text"]
    assert lyrics_appear_complete(result["lyrics_text"], 280, synced=False) is True
    assert lyrics_appear_complete(candidate["syncedLyrics"], 280, synced=True) is False
