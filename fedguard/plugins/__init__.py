"""Built-in default plugins: enough to confirm the pipeline works and to provide basic protection."""
from fedguard.plugins.accumulate import EvidenceAccumulator
from fedguard.plugins.actions import JumpRollback, NormClip, SampleMask
from fedguard.plugins.basic import ReportGuard, RobustOutlier
from fedguard.plugins.paired import CentroidConsensus, LocalCentroid
from fedguard.plugins.probe import ComplianceProbe
from fedguard.plugins.stats import EffectStats, FactorStats

BUILTIN = {p.name: p for p in (EffectStats, FactorStats, ReportGuard, RobustOutlier, ComplianceProbe,
                                  EvidenceAccumulator, CentroidConsensus, LocalCentroid, NormClip,
                                  JumpRollback, SampleMask)}

__all__ = ["BUILTIN", "CentroidConsensus", "ComplianceProbe", "EffectStats", "EvidenceAccumulator", "FactorStats", "JumpRollback", "LocalCentroid", "NormClip", "ReportGuard", "RobustOutlier", "SampleMask"]
