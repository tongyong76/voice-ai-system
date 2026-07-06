#include "http_upload.h"
#include "esp_http_client.h"
#include "esp_log.h"
#include "cJSON.h"
#include <string.h>
#include <stdlib.h>
#include <time.h>

static const char *TAG = "HTTP_UPLOAD";

#define SERVER_URL_MAX_LEN 256
#define UPLOAD_QUEUE_SIZE 10
#define MAX_AUDIO_SIZE 4096

static char server_url[SERVER_URL_MAX_LEN] = "http://192.168.1.100:8000";
static char device_code[32] = "ESP32_001";

typedef struct {
    uint8_t *data;
    size_t size;
    uint32_t timestamp;
} audio_item_t;

static audio_item_t upload_queue[UPLOAD_QUEUE_SIZE];
static int queue_head = 0;
static int queue_tail = 0;
static int queue_count = 0;

esp_err_t http_upload_init(void)
{
    ESP_LOGI(TAG, "Initializing HTTP upload");
    memset(upload_queue, 0, sizeof(upload_queue));

    // TODO: Read device_code from NVS or config
    // TODO: Read server_url from NVS or config

    return ESP_OK;
}

esp_err_t http_upload_set_server(const char *url)
{
    strncpy(server_url, url, SERVER_URL_MAX_LEN - 1);
    ESP_LOGI(TAG, "Server URL set to: %s", server_url);
    return ESP_OK;
}

esp_err_t http_upload_queue_add(const uint8_t *data, size_t size)
{
    if (queue_count >= UPLOAD_QUEUE_SIZE) {
        ESP_LOGW(TAG, "Upload queue full, dropping oldest item");
        // Free oldest item
        if (upload_queue[queue_head].data) {
            free(upload_queue[queue_head].data);
        }
        queue_head = (queue_head + 1) % UPLOAD_QUEUE_SIZE;
        queue_count--;
    }

    // Allocate and copy data
    uint8_t *copy = malloc(size);
    if (!copy) {
        ESP_LOGE(TAG, "Failed to allocate memory for audio data");
        return ESP_ERR_NO_MEM;
    }
    memcpy(copy, data, size);

    upload_queue[queue_tail].data = copy;
    upload_queue[queue_tail].size = size;
    upload_queue[queue_tail].timestamp = (uint32_t)time(NULL);

    queue_tail = (queue_tail + 1) % UPLOAD_QUEUE_SIZE;
    queue_count++;

    ESP_LOGI(TAG, "Audio queued: %d bytes, queue count: %d", size, queue_count);
    return ESP_OK;
}

static esp_err_t upload_audio(const uint8_t *data, size_t size)
{
    char url[SERVER_URL_MAX_LEN + 64];
    snprintf(url, sizeof(url), "%s/api/audio/upload?device_code=%s", server_url, device_code);

    esp_http_client_config_t config = {
        .url = url,
        .method = HTTP_METHOD_POST,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    if (!client) {
        ESP_LOGE(TAG, "Failed to init HTTP client");
        return ESP_FAIL;
    }

    // Set headers
    esp_http_client_set_header(client, "Content-Type", "application/octet-stream");

    // Set post data
    esp_http_client_set_post_field(client, (const char *)data, size);

    // Perform request
    esp_err_t err = esp_http_client_perform(client);

    if (err == ESP_OK) {
        int status_code = esp_http_client_get_status_code(client);
        ESP_LOGI(TAG, "Upload complete, status: %d", status_code);

        if (status_code != 200) {
            err = ESP_FAIL;
        }
    } else {
        ESP_LOGE(TAG, "Upload failed: %s", esp_err_to_name(err));
    }

    esp_http_client_cleanup(client);
    return err;
}

esp_err_t http_upload_process_queue(void)
{
    if (queue_count == 0) {
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Processing upload queue: %d items", queue_count);

    while (queue_count > 0) {
        audio_item_t *item = &upload_queue[queue_head];

        esp_err_t err = upload_audio(item->data, item->size);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Upload failed, will retry later");
            break;
        }

        // Free uploaded data
        free(item->data);
        item->data = NULL;
        item->size = 0;

        queue_head = (queue_head + 1) % UPLOAD_QUEUE_SIZE;
        queue_count--;
    }

    return ESP_OK;
}
