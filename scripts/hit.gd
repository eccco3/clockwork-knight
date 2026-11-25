class_name Hit
extends RefCounted
## One blow as it lands: who struck it, how hard, where and which way it was going, how far it shoves the one
## it lands on, and how long both of them hold still with it (hitstop).

var by: Health
var damage := 0.0
var at := Vector3.ZERO
## Level and unit length: the way the blow drives the one it lands on, away from the striker.
var way := Vector3.ZERO
var shove := 0.0
var stop := 0.0
