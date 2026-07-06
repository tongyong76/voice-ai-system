#include "opus_encoder.h"
#include "opus.h"
#include "esp_log.h"
#include <string.h>

static const char *TAG = "OPUS_ENCODER";

#define SAMPLE_RATE    16000
#define CHANNELS       1
#define FRAME_SIZE     320  // 20ms at 16kHz
#define BITRATE        24000

static OpusEncoder *encoder = NULL;

esp_err_t opus_encoder_init(void)
{
    ESP_LOGI(TAG, "Initializing Opus encoder");

    int error;
    encoder = opus_encoder_create(SAMPLE_RATE, CHANNELS, OPUS_APPLICATION_VOIP, &error);

    if (error != OPUS_OK || encoder == NULL) {
        ESP_LOGE(TAG, "Failed to create Opus encoder: %d", error);
        return ESP_FAIL;
    }

    // Configure encoder
    opus_encoder_ctl(encoder, OPUS_SET_BITRATE(BITRATE));
    opus_encoder_ctl(encoder, OPUS_SET_COMPLEXITY(5));
    opus_encoder_ctl(encoder, OPUS_SET_SIGNAL(OPUS_SIGNAL_VOICE));

    ESP_LOGI(TAG, "Opus encoder initialized successfully");
    return ESP_OK;
}

esp_err_t opus_encoder_encode(
    const int16_t *pcm_data,
    size_t pcm_samples,
    uint8_t *opus_buffer,
    size_t opus_buffer_size,
    size_t *opus_size)
{
    if (encoder == NULL) {
        return ESP_ERR_INVALID_STATE;
    }

    *opus_size = 0;
    size_t total_encoded = 0;
    size_t samples_processed = 0;

    while (samples_processed < pcm_samples) {
        size_t frame_size = pcm_samples - samples_processed;
        if (frame_size > FRAME_SIZE) {
            frame_size = FRAME_SIZE;
        }

        // Pad with zeros if frame is too small
        int16_t frame[FRAME_SIZE];
        memcpy(frame, &pcm_data[samples_processed], frame_size * sizeof(int16_t));
        if (frame_size < FRAME_SIZE) {
            memset(&frame[frame_size], 0, (FRAME_SIZE - frame_size) * sizeof(int16_t));
        }

        int encoded = opus_encode(encoder, frame, FRAME_SIZE,
                                  &opus_buffer[total_encoded],
                                  opus_buffer_size - total_encoded);

        if (encoded < 0) {
            ESP_LOGE(TAG, "Opus encoding failed: %d", encoded);
            return ESP_FAIL;
        }

        total_encoded += encoded;
        samples_processed += frame_size;
    }

    *opus_size = total_encoded;
    return ESP_OK;
}

esp_err_t opus_encoder_deinit(void)
{
    if (encoder != NULL) {
        opus_encoder_destroy(encoder);
        encoder = NULL;
    }
    return ESP_OK;
}
