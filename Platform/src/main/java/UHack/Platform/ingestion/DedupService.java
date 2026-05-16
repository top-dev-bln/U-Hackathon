package UHack.Platform.ingestion;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;

@Service
public class DedupService {

    private static final String KEY_PREFIX = "wyscout:event:seen:";

    private final StringRedisTemplate redis;
    private final Duration ttl;

    public DedupService(StringRedisTemplate redis,
                        @Value("${wyscout.dedup.ttl-seconds}") long ttlSeconds) {
        this.redis = redis;
        this.ttl = Duration.ofSeconds(ttlSeconds);
    }

    /**
     * Atomic "claim" of an event id. Returns true only if we are the first
     * to see this id within the TTL window (SET NX EX under the hood).
     */
    public boolean markIfAbsent(String eventId) {
        Boolean ok = redis.opsForValue().setIfAbsent(KEY_PREFIX + eventId, "1", ttl);
        return Boolean.TRUE.equals(ok);
    }
}
