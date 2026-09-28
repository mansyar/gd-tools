extends RefCounted

## Small subject exercised by the bridge coverage suite so the plan has a
## measurable source file outside the excluded test directories.


func double(value: int) -> int:
	return value * 2


func gate(value: int) -> String:
	if value > 10:
		return "high"
	return "low"
