Initial study reached the final fixed adverse-perturbation diagnostic but a
ScenarioDraw deepcopy constructor failed before summary output was saved.
The original pre-final selection lock is preserved. Retry fixes only array
copying, with identical seeds/search/parameters/judge and no final tuning.
The retried selection will be compared exactly with the original lock.
