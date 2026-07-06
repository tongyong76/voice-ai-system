#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_err.h"
#include "nvs_flash.h"

#include "audio/i2s_input.h"
#include "audio/opus_encoder.h"
#include "network/wifi_manager.h"
#include "network/http_upload.h"
#include "config/device_config.h"

static const char *TAG = "MAIN";

// Task handles
static TaskHandle_t audio_task_handle = NULL;
static TaskHandle_t upload_task_handle = NULL;

// Audio buffer
#define AUDIO_BUFFER_SIZE (16000 * 5 * 2)  // 5 seconds of 16kHz 16-bit audio
static int16_t audio_buffer[AUDIO_BUFFER_SIZE / 2];
static size_t audio_buffer_pos = 0;

static void audio采集_task(void *arg)
{
    ESP_LOGI(TAG, "Audio采集 task started");

    while (1) {
        // Read audio from I2S
        size_t bytes_read = 0;
        esp_err_t ret = i2s_input_read(
            (uint8_t *)&audio_buffer[audio_buffer_pos],
            1024,
            &bytes_read,
            1000 / portTICK_PERIOD_MS
        );

        if (ret == ESP_OK && bytes_read > 0) {
            audio_buffer_pos += bytes_read / 2;

            // Check if buffer is full (5 seconds)
            if (audio_buffer_pos >= AUDIO_BUFFER_SIZE / 2) {
                // Encode to Opus
                uint8_t opus_buffer[4096];
                size_t opus_size = 0;

                ret = opus_encoder_encode(
                    audio_buffer,
                    audio_buffer_pos,
                    opus_buffer,
                    sizeof(opus_buffer),
                    &opus_size
                );

                if (ret == ESP_OK && opus_size > 0) {
                    // Queue for upload
                    http_upload_queue_add(opus_buffer, opus_size);
                    ESP_LOGI(TAG, "Audio chunk queued: %d bytes", opus_size);
                }

                audio_buffer_pos = 0;
            }
        }

        vTaskDelay(10 / portTICK_PERIOD_MS);
    }
}

static void upload_task(void *arg)
{
    ESP_LOGI(TAG, "Upload task started");

    while (1) {
        // Wait for Wi-Fi connection
        if (!wifi_manager_is_connected()) {
            vTaskDelay(1000 / portTICK_PERIOD_MS);
            continue;
        }

        // Upload queued audio
        http_upload_process_queue();

        vTaskDelay(100 / portTICK_PERIOD_MS);
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "Voice AI Edge Device Starting...");

    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // Initialize device config
    device_config_init();

    // Initialize Wi-Fi
    wifi_manager_init();

    // Initialize I2S input
    i2s_input_init();

    // Initialize Opus encoder
    opus_encoder_init();

    // Initialize HTTP upload
    http_upload_init();

    // Create tasks
    xTaskCreatePinnedToCore(
        audio采集_task,
        "audio采集",
        8192,
        NULL,
        5,
        &audio_task_handle,
        1  // Core 1
    );

    xTaskCreatePinnedToCore(
        upload_task,
        "upload",
        8192,
        NULL,
        3,
        &upload_task_handle,
        0  // Core 0
    );

    ESP_LOGI(TAG, "System initialized successfully");
}
