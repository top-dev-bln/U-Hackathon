package UHack.Platform.ingestion;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Service
public class EventPublisher {

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final String topic;

    public EventPublisher(KafkaTemplate<String, String> kafkaTemplate,
                          @Value("${wyscout.kafka.topic}") String topic) {
        this.kafkaTemplate = kafkaTemplate;
        this.topic = topic;
    }

    public void publish(String eventId, String payload) {
        kafkaTemplate.send(topic, eventId, payload);
    }
}
