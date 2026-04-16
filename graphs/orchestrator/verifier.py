from graphs.verify import verify_files


def run_verifier(files: list[str], project_context: dict, skill_id: str) -> dict:
    return verify_files(
        files=files,
        project_context=project_context,
        mode="full",
        skill_id=skill_id,
    )
