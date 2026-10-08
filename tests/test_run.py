import json
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from concerted_abduction.types import (
    BpaOutput,
    CombinedMasses,
    FocalSetMass,
    SourceBpa,
    DataSample,
    DataSet,
    FocalSetOutput,
    FodOutput,
    FrameOfDiscernment,
)
from scripts import run
from config.settings import ComponentConfig, ConcertedAbductionSettings


class PipelineRunnerTests(unittest.TestCase):
    @patch.object(Path, "write_text")
    @patch.object(run, "save_bpa")
    @patch.object(run, "create_bpa_assigner")
    @patch.object(run, "save_focal_sets")
    @patch.object(run, "save_frame")
    @patch.object(run, "save_run_metadata")
    @patch.object(run, "make_run_dir", return_value=Path("/tmp/pipeline-run"))
    @patch.object(run, "latest_run_dir", return_value=Path("/tmp/data-run"))
    @patch.object(run, "load_dataset")
    @patch.object(run, "create_focal_set_creator")
    @patch.object(run, "create_extractor")
    @patch.object(run, "ConcertedAbductionSettings")
    @patch.object(run, "ENVSettings")
    def test_main_continues_to_bpa_with_focal_set_warnings(
        self,
        env_settings: Mock,
        settings_cls: Mock,
        create_extractor: Mock,
        create_focal_set_creator: Mock,
        load_dataset: Mock,
        latest_run_dir: Mock,
        make_run_dir: Mock,
        save_run_metadata: Mock,
        save_frame: Mock,
        save_focal_sets: Mock,
        create_bpa_assigner: Mock,
        save_bpa: Mock,
        write_text: Mock,
    ) -> None:
        env_settings.return_value.gemini_api_key = None
        component_cfg = SimpleNamespace(
            type="stub",
            llm=None,
            prompt_path=None,
            model_dump=lambda **kwargs: {},
            output_dir=Path("/tmp/outputs"),
        )
        settings_cls.return_value = SimpleNamespace(
            data_generator=SimpleNamespace(output_dir=Path("/tmp/data")),
            fod_extractor=component_cfg,
            focal_set=component_cfg,
            bpa=component_cfg,
            combiner=ComponentConfig(type="Dempster", output_dir=component_cfg.output_dir),
        )
        sample = DataSample(
            scenario_id="scenario-1",
            created_at="2026-08-24",
            input_message="Question",
            outputs=[],
        )
        load_dataset.return_value = DataSet(samples=[sample])

        fod_result = FodOutput(
            hypotheses={"source": "response"},
            frame=FrameOfDiscernment(frame=["hypothesis"]),
        )
        focal_set_result = FocalSetOutput(
            sources=[], validation_errors=["Citation is not a verbatim excerpt"]
        )
        extractor = create_extractor.return_value
        extractor.generate_frame.return_value = fod_result
        creator = create_focal_set_creator.return_value
        creator.create_focal_sets.return_value = focal_set_result

        create_bpa_assigner.return_value.assign_masses.return_value = BpaOutput(
            sources=[SourceBpa(source="source", masses=[FocalSetMass(
                hypotheses=["hypothesis"], mass=1, justification="Test",
            )])]
        )
        self.assertEqual(run.main([]), 0)

        extractor.generate_frame.assert_called_once_with(sample)
        creator.create_focal_sets.assert_called_once_with(fod_result)
        create_bpa_assigner.return_value.assign_masses.assert_called_once_with(
            fod_result, focal_set_result
        )
        save_bpa.assert_called_once_with(
            Path("/tmp/pipeline-run"), "scenario-1",
            create_bpa_assigner.return_value.assign_masses.return_value,
        )
        save_frame.assert_called_once_with(
            Path("/tmp/pipeline-run"), "scenario-1", fod_result
        )
        save_focal_sets.assert_called_once_with(
            Path("/tmp/pipeline-run"), "scenario-1", focal_set_result
        )

    def test_failures_are_logged_and_later_scenarios_run(self):
        for stage in ("frame", "focal_sets", "bpa", "combination", None):
            with self.subTest(stage=stage), TemporaryDirectory() as directory:
                root = Path(directory)
                cfg = SimpleNamespace(
                    type="stub", llm=None, prompt_path=None, output_dir=root,
                    model_dump=lambda **kwargs: {},
                )
                settings = SimpleNamespace(
                    data_generator=cfg, fod_extractor=cfg, focal_set=cfg, bpa=cfg,
                    combiner=ComponentConfig(type="Dempster", output_dir=root),
                )
                samples = [DataSample(
                    scenario_id=f"scenario-{i}", created_at="2026-10-08",
                    input_message="Question", outputs=[],
                ) for i in range(2)]
                fod = FodOutput(hypotheses={"a": "response"},
                                frame=FrameOfDiscernment(frame=["x", "y"]))
                focal = FocalSetOutput()
                bpa = BpaOutput(sources=[SourceBpa(source="a", masses=[
                    FocalSetMass(hypotheses=["x"], mass=1, justification="Test")
                ])])
                extractor, creator, assigner = Mock(), Mock(), Mock()
                extractor.generate_frame.return_value = fod
                creator.create_focal_sets.return_value = focal
                assigner.assign_masses.return_value = bpa
                failing_call = {
                    "frame": extractor.generate_frame,
                    "focal_sets": creator.create_focal_sets,
                    "bpa": assigner.assign_masses,
                }
                if stage == "combination":
                    conflicting = BpaOutput(sources=bpa.sources + [SourceBpa(
                        source="b", masses=[FocalSetMass(
                            hypotheses=["y"], mass=1, justification="Conflicting evidence",
                        )],
                    )])
                    assigner.assign_masses.side_effect = [conflicting, bpa]
                elif stage is not None:
                    result = {"frame": fod, "focal_sets": focal, "bpa": bpa}[stage]
                    failing_call[stage].side_effect = [ValueError("Test failure"), result]
                with (
                    patch.object(run, "ENVSettings", return_value=SimpleNamespace(gemini_api_key=None)),
                    patch.object(run, "ConcertedAbductionSettings", return_value=settings),
                    patch.object(run, "latest_run_dir", return_value=root),
                    patch.object(run, "load_dataset", return_value=DataSet(samples=samples)),
                    patch.object(run, "make_run_dir", return_value=root),
                    patch.object(run, "create_extractor", return_value=extractor),
                    patch.object(run, "create_focal_set_creator", return_value=creator),
                    patch.object(run, "create_bpa_assigner", return_value=assigner),
                ):
                    self.assertEqual(run.main(["--all"]), 1 if stage else 0)
                self.assertTrue((root / "scenario-1_bpa.json").exists())
                combined = json.loads((root / "scenario-1_combined.json").read_text())
                masses = CombinedMasses.model_validate(combined)
                self.assertEqual(masses.combined_masses[0].focal_set, {"x"})
                self.assertEqual(masses.combined_masses[0].combined_mass, 1.0)
                self.assertEqual(combined["conflict"], 0.0)
                metadata = json.loads((root / "metadata.json").read_text())
                self.assertEqual(metadata["combiner"]["type"], "Dempster")
                summary = json.loads((root / "summary.json").read_text())
                self.assertEqual(summary["completed"], 1 if stage else 2)
                self.assertEqual(summary["failed"], 1 if stage else 0)
                error_path = root / "scenario-0_error.json"
                if stage is not None:
                    error = json.loads(error_path.read_text())
                    self.assertEqual(error, {
                        "scenario_id": "scenario-0", "status": "failed", "stage": stage,
                        "error_type": "ValueError",
                        "message": ("Dempster combination is undefined under total conflict (k=1)."
                                    if stage == "combination" else "Test failure"),
                    })
                    self.assertEqual(summary["scenarios"][0], error)
                    self.assertEqual((root / "scenario-0_bpa.json").exists(), stage == "combination")
                    self.assertFalse((root / "scenario-0_combined.json").exists())
                    if stage in ("focal_sets", "bpa", "combination"):
                        self.assertTrue((root / "scenario-0_frame.json").exists())
                    if stage in ("bpa", "combination"):
                        self.assertTrue((root / "scenario-0_focal_sets.json").exists())
                else:
                    self.assertFalse(error_path.exists())
                    self.assertTrue((root / "scenario-0_bpa.json").exists())

    def test_configured_combiner_and_unknown_method(self):
        settings = ConcertedAbductionSettings()  # pyright: ignore[reportCallIssue]
        combiner = run.create_combiner(settings.combiner)
        self.assertEqual(type(combiner).__name__, "DempsterCombination")
        self.assertEqual(settings.combiner.output_dir, settings.bpa.output_dir)
        with self.assertRaisesRegex(ValueError, "Unknown combiner"):
            run.create_combiner(ComponentConfig(type="unknown", output_dir=Path("experiments/runs")))

    @patch.object(run, "load_dataset", side_effect=ValueError("Unreadable dataset"))
    @patch.object(run, "latest_run_dir", return_value=Path("/tmp/data-run"))
    @patch.object(run, "ENVSettings")
    def test_setup_failure_stops_run(self, env: Mock, latest: Mock, load: Mock):
        env.return_value.gemini_api_key = "test"
        with self.assertRaisesRegex(ValueError, "Unreadable dataset"):
            run.main(["--all"])


if __name__ == "__main__":
    unittest.main()
