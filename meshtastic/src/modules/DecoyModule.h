#pragma once
#include "configuration.h"

#if !MESHTASTIC_EXCLUDE_DECOY

#include "MeshPacketQueue.h"
#include "concurrency/OSThread.h"
#include "mesh/generated/meshtastic/mesh.pb.h"

/**
 * Decoy Module – emits randomised fake LoRa packets to provide traffic-analysis
 * resistance.  When a real user-originated packet is sent the module schedules a
 * configurable number of decoy transmissions on the same channel with random
 * post-send delays drawn from [0, post_window_ms].  Optionally it can also emit
 * periodic ambient decoys regardless of real sends.
 *
 * Key config fields (meshtastic_ModuleConfig_DecoyConfig):
 *   enabled            – master switch
 *   num_decoys         – decoys to schedule per real-send trigger (default 3)
 *   post_window_ms     – upper bound of the random delay window in ms (default 5000)
 *   is_real_emitter    – when true the module suppresses burst decoys on own sends
 *                        (set this on the node that is the actual message source)
 *   ambient_interval_secs – if >0 fire ambient decoys at this cadence even with
 *                           no real sends (for nodes acting as decoy nodes)
 */
class DecoyModule : private concurrency::OSThread
{
  public:
    DecoyModule();

    /**
     * Called by MeshService::sendToMesh() immediately before handing the packet
     * to the router, so we can snapshot the metadata before ownership transfers.
     *
     * Schedules a burst of decoy transmissions unless is_real_emitter is set.
     */
    void onUserPacketSent(const meshtastic_MeshPacket *p);

  protected:
    int32_t runOnce() override;

  private:
    static constexpr uint8_t MAX_PENDING = 8;

    struct PendingDecoy {
        meshtastic_PortNum portnum;
        pb_size_t payload_size;
        uint8_t channel;
        uint8_t hop_limit;
        uint32_t fire_at_ms;
        bool valid;
    };

    PendingDecoy _queue[MAX_PENDING];
    uint32_t _ambientNextMs = 0;

    void scheduleDecoys(meshtastic_PortNum portnum, pb_size_t payload_size, uint8_t channel, uint8_t hop_limit, uint32_t count,
                        uint32_t window_ms);
    void sendDecoyPacket(meshtastic_PortNum portnum, pb_size_t payload_size, uint8_t channel, uint8_t hop_limit);
    bool enqueuePending(meshtastic_PortNum portnum, pb_size_t payload_size, uint8_t channel, uint8_t hop_limit,
                        uint32_t fire_at_ms);
};

extern DecoyModule *decoyModule;

#endif // !MESHTASTIC_EXCLUDE_DECOY
