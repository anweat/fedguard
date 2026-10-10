"""Operators: the reusable computations defenses are composed of.

Stateless functions on tensors, state dicts and plain numbers. They know nothing about stages, plugins
or frameworks; a method plugin is an arrangement of these plus the views the runtime gives it.

  states      arithmetic on LoRA state dicts (delta, flatten, norm, weighted average)
  geometry    distances, cosines, Gram matrices, Krum scores, cross-sectional comparison
  lowrank     exact norms, inner products and spectra of LoRA products without densifying
  robust      median/MAD scores, coordinate median, trimmed mean, geometric median, gap thresholds
  transform   DCT and low-pass, PCA, random projection, normalization
  cluster     k-means, agglomerative, DBSCAN, majority cluster, silhouette, gap statistic
  density     1-D kernel density and valley thresholds, entropy, Jensen-Shannon divergence
  spectral    top-singular-direction scores, spectral entropy, effective rank
  sequential  CUSUM, Beta trust counts, exponential averages
  update      clip, scale, noise, projection of updates and gradients
  sampling    seeded subsampling of samples, clients and coordinates
  text        model-free text features
  probe       linear probes on features (fit and apply)
"""
