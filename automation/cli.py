"""
OmniSight Automation CLI Entrypoint.
Enables one-command execution of browser navigation, evidence collection, and visual audit.
"""

import sys
import json
import argparse
from typing import List
from automation.config import config
from automation.orchestrator import Orchestrator
from automation.vlm_adapter import MockVLMAdapter, LiveVLMAdapter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OmniSight Browser Automation & Visual QA Runner"
    )
    parser.add_argument(
        "--target",
        type=str,
        default=config.app_url,
        help=f"Target web app URL (default: {config.app_url})",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="checkout_flow",
        help="Target journey scenario to execute (default: checkout_flow)",
    )
    parser.add_argument(
        "--viewports",
        nargs="+",
        default=None,
        help="Specific viewports to run (e.g., desktop_1440x900 mobile_375x667)",
    )
    parser.add_argument(
        "--use-live-vlm",
        action="store_true",
        help="Call live multimodal VLM API instead of deterministic mock adapter",
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Print final output strictly in JSON format",
    )
    parser.add_argument(
        "--no-retest",
        action="store_true",
        help="Skip closed-loop sandboxed retest verification",
    )
    parser.add_argument(
        "--sync-backend",
        action="store_true",
        help="Synchronize audit progress, findings, and patch with FastAPI backend gateway",
    )
    parser.add_argument(
        "--backend-url",
        type=str,
        default=config.backend_url,
        help=f"FastAPI backend gateway URL (default: {config.backend_url})",
    )

    args = parser.parse_args()

    backend_client = None
    backend_status_str = "Standalone Local Mode"
    if args.sync_backend:
        from automation.backend_client import BackendClient
        backend_client = BackendClient(base_url=args.backend_url)
        if backend_client.check_health():
            backend_status_str = f"Connected ({args.backend_url})"
        else:
            backend_status_str = f"Offline ({args.backend_url}) - local fallback"

    vlm = LiveVLMAdapter() if args.use_live_vlm else MockVLMAdapter()
    orchestrator = Orchestrator(
        vlm_adapter=vlm,
        backend_client=backend_client,
        sync_backend=args.sync_backend,
    )

    if not args.json_output:
        print("=" * 60)
        print("  OmniSight Autonomous Visual QA & RPA Agent")
        print("=" * 60)
        print(f"Target URL: {args.target}")
        print(f"Scenario:   {args.scenario}")
        print(f"Engine:     Playwright Chromium (Headless: {config.headless})")
        print(f"VLM:        {'Live Multimodal API' if args.use_live_vlm else 'Deterministic Mock'}")
        print(f"Retest:     {'Disabled' if args.no_retest else 'Sandboxed Verification Enabled'}")
        print(f"Backend:    {backend_status_str}")
        print("-" * 60)
        print("Starting e-commerce journey and evidence capture...")

    result = orchestrator.run_full_remediation_loop(
        target_url=args.target,
        scenario=args.scenario,
        viewports=args.viewports,
        auto_retest=not args.no_retest,
    )

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        status = result.get("status", "unknown")
        print("-" * 60)
        print(f"Run Completed: {result.get('run_id')}")
        if args.no_retest and status == "audited":
            print("Final Status:  AUDITED (Retest skipped via --no-retest)")
        else:
            print(f"Final Status:  {status.upper()}")
        if result.get("error"):
            print(f"Error:         {result['error']}")
        print(f"Screenshots:   {result.get('screenshots_count', 0)} files saved")
        findings = result.get("findings", [])
        print(f"Defects Found: {len(findings)}")

        for idx, f in enumerate(findings, 1):
            print(f"  [{idx}] {f['category'].upper()} ({f['severity'].upper()}): {f['description']}")
            print(f"      Target: {f.get('target_element')} | Viewport: {f['viewport']}")
            print(f"      Fix:    {f['suggested_change']}")

        retest = result.get("retest_verification")
        if retest:
            print("\nRetest Verification:")
            print(f"  Status:   {retest.get('status', '').upper()}")
            print(f"  Delta:    {retest.get('mismatch_percentage', 0.0)}% pixel difference")
            print(f"  Viewport: {retest.get('target_viewport')}")
            if retest.get("notes"):
                print(f"  Notes:    {retest.get('notes')}")

        annotated = result.get("annotated_screenshots", [])
        if annotated:
            print(f"\nAnnotated Overlays: {len(annotated)} bounding-box defect overlays generated")

        if args.sync_backend and backend_client and result.get("run_id"):
            print(f"\nBackend Run:   {args.backend_url}/runs/{result.get('run_id')}")

        if result.get("artifacts_dir"):
            print(f"\nArtifacts stored in: {result['artifacts_dir']}")
        print("=" * 60)

    return 0 if result.get("status") in ("fixed", "audited") else 1


if __name__ == "__main__":
    sys.exit(main())
