package UHack.Platform.ingestion;

import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;
import java.util.Collections;
import java.util.List;
import java.util.stream.StreamSupport;

@Component
public class WyscoutClient {

    private final RestTemplate restTemplate;
    private final String apiUrl;

    public WyscoutClient(RestTemplateBuilder builder,
                         @Value("${wyscout.api.url}") String apiUrl) {
        this.restTemplate = builder
                .connectTimeout(Duration.ofSeconds(3))
                .readTimeout(Duration.ofSeconds(10))
                .build();
        this.apiUrl = apiUrl;
    }

    public List<JsonNode> fetchEvents() {
        JsonNode body = restTemplate.getForObject(apiUrl, JsonNode.class);
        if (body == null) {
            return Collections.emptyList();
        }
        JsonNode events = body.isArray() ? body : body.path("events");
        if (!events.isArray()) {
            return Collections.emptyList();
        }
        return StreamSupport.stream(events.spliterator(), false).toList();
    }
}
