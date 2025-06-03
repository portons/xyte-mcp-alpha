-- KEYS[1] = rl:{key_id} ; ARGV[1] = limit ; ARGV[2] = ttl(seconds)
local c = redis.call("INCR", KEYS[1])
if c == 1 then redis.call("EXPIRE", KEYS[1], ARGV[2]) end
if c > tonumber(ARGV[1]) then return 0 else return tonumber(ARGV[1]) - c end
