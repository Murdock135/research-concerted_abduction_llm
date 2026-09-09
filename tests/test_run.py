import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from concerted_abduction.types import (
    DataSample,
    DataSet,
    FocalSetOutput,
    FodOutput,
    FrameOfDiscernment,
)
from scripts import run


class PipelineRunnerTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
