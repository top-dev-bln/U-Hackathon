package UHack.Platform.ingestion;

import com.fasterxml.jackson.databind.JsonNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class WyscoutPollingService {

    private static final Logger log = LoggerFactory.getLogger(WyscoutPollingService.class);

    private final WyscoutClient client;
    private final DedupService dedup;
    private final EventPublisher publisher;

    public WyscoutPollingService(WyscoutClient client,
                                 DedupService dedup,
                                 EventPublisher publisher) {
        this.client = client;
        this.dedup = dedup;
        this.publisher = publisher;
    }

    @Scheduled(fixedDelayString = "${wyscout.poll.interval-ms}")
    public void poll() {
        List<JsonNode> events;
        try {
            events = client.fetchEvents();
        } catch (Exception e) {
            log.warn("Wyscout fetch failed: {}", e.getMessage());
            return;
        }

        int fetched = events.size();
        int published = 0;
        int skipped = 0;

        for (JsonNode event : events) {
            JsonNode idNode = event.get("id");
            if (idNode == null || idNode.isNull()) {
                continue;
            }
            String eventId = idNode.asText();
            if (!dedup.markIfAbsent(eventId)) {
                skipped++;
                continue;
            }
            publisher.publish(eventId, event.toString());
            published++;
        }

        if (fetched > 0) {
            log.info("Poll cycle: fetched={}, published={}, deduped={}", fetched, published, skipped);
        }
    }
}
