#include "DecoyModule.h"
#include "configuration.h"

#if !MESHTASTIC_EXCLUDE_DECOY

#include "MeshService.h"
#include "NodeDB.h"
#include "mesh/Router.h"
#include "airtime.h"
#include "graphics/Screen.h"
#include "meshUtils.h"

DecoyModule *decoyModule = nullptr;

DecoyModule::DecoyModule() : concurrency::OSThread("DecoyModule")
{
    memset(_queue, 0, sizeof(_queue));
}

void DecoyModule::onUserPacketSent(const meshtastic_MeshPacket *p)
{
    if (!moduleConfig.has_decoy || !moduleConfig.decoy.enabled)
        return;

    // is_real_emitter suppresses burst decoys on own sends
    if (moduleConfig.decoy.is_real_emitter)
        return;

    uint32_t count = moduleConfig.decoy.num_decoys > 0 ? moduleConfig.decoy.num_decoys : 3;
    uint32_t window = moduleConfig.decoy.post_window_ms > 0 ? moduleConfig.decoy.post_window_ms : 5000;

    meshtastic_PortNum portnum = meshtastic_PortNum_UNKNOWN_APP;
    pb_size_t payload_size = 0;
    uint8_t channel = 0;
    uint8_t hop_limit = config.lora.hop_limit;

    if (p->which_payload_variant == meshtastic_MeshPacket_decoded_tag) {
        portnum = p->decoded.portnum;
        payload_size = p->decoded.payload.size;
        channel = p->channel;
        hop_limit = p->hop_limit;
    }

    scheduleDecoys(portnum, payload_size, channel, hop_limit, count, window);
    setInterval(1); // wake up soon to dispatch pending decoys
}

bool DecoyModule::enqueuePending(meshtastic_PortNum portnum, pb_size_t payload_size, uint8_t channel, uint8_t hop_limit,
                                 uint32_t fire_at_ms)
{
    for (uint8_t i = 0; i < MAX_PENDING; i++) {
        if (!_queue[i].valid) {
            _queue[i] = {portnum, payload_size, channel, hop_limit, fire_at_ms, true};
            return true;
        }
    }
    return false; // queue full, drop this decoy
}

void DecoyModule::scheduleDecoys(meshtastic_PortNum portnum, pb_size_t payload_size, uint8_t channel, uint8_t hop_limit,
                                 uint32_t count, uint32_t window_ms)
{
    uint32_t now = millis();
    for (uint32_t i = 0; i < count; i++) {
        uint32_t delay = (uint32_t)(random(window_ms + 1));
        if (!enqueuePending(portnum, payload_size, channel, hop_limit, now + delay))
            break; // queue full
    }
}

void DecoyModule::sendDecoyPacket(meshtastic_PortNum portnum, pb_size_t payload_size, uint8_t channel, uint8_t hop_limit)
{
    if (!airTime->isTxAllowedChannelUtil(false))
        return;
    if (!airTime->isTxAllowedAirUtil())
        return;

    meshtastic_MeshPacket *p = packetPool.allocZeroed();
    if (!p)
        return;

    p->to = NODENUM_BROADCAST;
    p->channel = channel;
    p->hop_limit = hop_limit;
    p->want_ack = false;
    p->id = generatePacketId();
    p->which_payload_variant = meshtastic_MeshPacket_decoded_tag;
    p->decoded.portnum = portnum;

    // Fill the payload with random bytes so decoys are indistinguishable from real packets
    pb_size_t sz = payload_size > 0 ? payload_size : 1;
    if (sz > sizeof(p->decoded.payload.bytes))
        sz = sizeof(p->decoded.payload.bytes);
    p->decoded.payload.size = sz;
    for (pb_size_t i = 0; i < sz; i++)
        p->decoded.payload.bytes[i] = (uint8_t)random(256);

    router->sendLocal(p, RX_SRC_LOCAL);

    char banner[32];
    snprintf(banner, sizeof(banner), "Decoy TX\nch:%d sz:%d", (int)channel, (int)sz);
    IF_SCREEN(screen->showSimpleBanner(banner, 2000));
    LOG_DEBUG("[Decoy] TX ch=%d portnum=%d sz=%d", (int)channel, (int)portnum, (int)sz);
}

int32_t DecoyModule::runOnce()
{
    if (!moduleConfig.has_decoy || !moduleConfig.decoy.enabled)
        return INT32_MAX;

    uint32_t now = millis();
    int32_t next_wake = INT32_MAX;

    // Dispatch any due pending decoys
    for (uint8_t i = 0; i < MAX_PENDING; i++) {
        if (!_queue[i].valid)
            continue;
        if ((int32_t)(_queue[i].fire_at_ms - now) <= 0) {
            sendDecoyPacket(_queue[i].portnum, _queue[i].payload_size, _queue[i].channel, _queue[i].hop_limit);
            _queue[i].valid = false;
        } else {
            int32_t remaining = (int32_t)(_queue[i].fire_at_ms - now);
            if (remaining < next_wake)
                next_wake = remaining;
        }
    }

    // Handle ambient (periodic) decoys
    uint32_t ambient_secs = moduleConfig.decoy.ambient_interval_secs;
    if (ambient_secs > 0) {
        if (_ambientNextMs == 0)
            _ambientNextMs = now + ambient_secs * 1000UL;

        if ((int32_t)(_ambientNextMs - now) <= 0) {
            _ambientNextMs = now + ambient_secs * 1000UL;
            sendDecoyPacket(meshtastic_PortNum_UNKNOWN_APP, 0, 0, config.lora.hop_limit);
        }

        int32_t ambient_remaining = (int32_t)(_ambientNextMs - now);
        if (ambient_remaining > 0 && ambient_remaining < next_wake)
            next_wake = ambient_remaining;
    }

    return next_wake > 0 ? next_wake : 1;
}

#endif // !MESHTASTIC_EXCLUDE_DECOY
