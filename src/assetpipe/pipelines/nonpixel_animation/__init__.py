"""Explicit nonpixel continuation through the existing Factory motion coordinator."""
STATUS = 'SUPPORTED_EXPERIMENTAL'

def run(*, job, plan_sha256, output, root, authorization=None,
        authorize_generation=False, allowed_roots=None):
    from ...providers.cli_runner import assert_not_nested
    from ...factory.motion import run_job
    assert_not_nested()
    if not job or not plan_sha256 or output is None:
        raise ValueError('NONPIXEL_ANIMATION requires an explicit job, pinned plan and new output')
    return run_job(job, plan_sha256, output, root, authorization=authorization,
                   authorize_generation=authorize_generation, allowed_roots=allowed_roots)
