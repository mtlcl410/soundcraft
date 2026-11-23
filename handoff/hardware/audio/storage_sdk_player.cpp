// Local diagnostic. Link the Steinberg SDK host sources directly.
#define NOMINMAX
#include <windows.h>
#include "asiosys.h"
#include "asio.h"
#include "asiodrivers.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <stdexcept>
#include <vector>

namespace {
constexpr int frames = 256, rate = 48000;
constexpr size_t capacity = 1u << 20;
struct Record { int64_t qpc; uint64_t position; int32_t flags, index; };
static_assert(sizeof(Record) == 24);
std::vector<Record> records(capacity);
std::atomic<size_t> published{};
std::atomic<unsigned> resets{}, resyncs{}, rates{};
std::vector<ASIOBufferInfo> buffers;
std::array<unsigned char, 12000 * 3> tone{};
size_t sample = 0;
bool output_ready = false;

void check(ASIOError status, const char *op) {
    if (status != ASE_OK) { std::fprintf(stderr,"%s returned %ld\n",op,long(status)); std::exit(2); }
}
void render(long index, const AsioTimeInfo &time, LARGE_INTEGER stamp) {
    const size_t i = published.load(std::memory_order_relaxed);
    if (i < capacity) {
        uint64_t pos = uint64_t(time.samplePosition.hi) << 32 | time.samplePosition.lo;
        records[i] = {stamp.QuadPart, pos, int32_t(time.flags), int32_t(index)};
        published.store(i+1, std::memory_order_release);
    }
    auto *left = static_cast<unsigned char*>(buffers[buffers.size()-2].buffers[index]);
    auto *right = buffers.back().buffers[index];
    for (int j=0; j<frames; ++j) {
        size_t phase = (sample+j) % (8*rate);
        if (phase < tone.size()/3) std::memcpy(left+3*j, tone.data()+phase*3, 3);
        else std::memset(left+3*j, 0, 3);
    }
    std::memcpy(right,left,3*frames);
    sample += frames;
    if (output_ready) ASIOOutputReady();
}
ASIOTime* timed(ASIOTime *t, long index, ASIOBool) {
    LARGE_INTEGER stamp; QueryPerformanceCounter(&stamp);
    render(index,t->timeInfo,stamp);
    return t;
}
void simple(long index, ASIOBool) {
    LARGE_INTEGER stamp; QueryPerformanceCounter(&stamp);
    AsioTimeInfo t{};
    if (ASIOGetSamplePosition(&t.samplePosition,&t.systemTime)==ASE_OK) t.flags=kSamplePositionValid|kSystemTimeValid;
    render(index,t,stamp);
}
long message(long what, long value, void*, double*) {
    if (what == kAsioSelectorSupported) return value==kAsioSupportsTimeInfo || value==kAsioEngineVersion;
    if (what == kAsioEngineVersion) return 2;
    if (what == kAsioSupportsTimeInfo) return 1;
    if (what == kAsioResetRequest) ++resets;
    if (what == kAsioResyncRequest) ++resyncs;
    return 0;
}
void changed(ASIOSampleRate) { ++rates; }
}

extern bool loadAsioDriver(char *name);
int main() {
    char driver[]="Model Mixer ASIO";
    if (!loadAsioDriver(driver)) { std::fprintf(stderr,"Cannot load Model Mixer ASIO\n"); return 2; }
    ASIODriverInfo info{}; info.asioVersion=2; info.sysRef=GetDesktopWindow();
    check(ASIOInit(&info),"init");
    check(ASIOSetSampleRate(rate),"set rate");
    ASIOSampleRate actual{}; check(ASIOGetSampleRate(&actual),"read rate");
    long inputs,outputs,min,max,preferred,granularity;
    check(ASIOGetChannels(&inputs,&outputs),"channels");
    check(ASIOGetBufferSize(&min,&max,&preferred,&granularity),"buffer sizes");
    if (actual!=rate || preferred!=frames || inputs<9 || outputs<2) return 3;
    buffers.resize(inputs+2);
    for (size_t i=0; i<buffers.size(); ++i) {
        auto &b=buffers[i]; b.isInput=i<size_t(inputs); b.channelNum=b.isInput?long(i):long(i)-inputs;
        ASIOChannelInfo channel{}; channel.isInput=b.isInput; channel.channel=b.channelNum;
        check(ASIOGetChannelInfo(&channel),"channel format");
        if (channel.type!=ASIOSTInt24LSB) return 3;
    }
    for (size_t i=0; i<tone.size()/3; ++i) {
        double env=std::min(1.,double(i)/96)*std::exp(-double(i)/4800);
        int32_t v=int32_t(160000*env*std::sin(6.283185307179586*440*i/rate));
        std::memcpy(tone.data()+3*i,&v,3);
    }
    ASIOCallbacks callbacks{simple,changed,message,timed};
    check(ASIOCreateBuffers(buffers.data(),long(buffers.size()),frames,&callbacks),"create duplex buffers");
    long inlat,outlat; check(ASIOGetLatencies(&inlat,&outlat),"latencies");
    output_ready=ASIOOutputReady()==ASE_OK;
    LARGE_INTEGER hz; QueryPerformanceFrequency(&hz);
    std::ofstream("native.json")<<"{\"device\":\"Model Mixer ASIO\",\"sample_rate\":"<<actual
      <<",\"preferred\":"<<preferred<<",\"buffer_frames\":"<<frames<<",\"inputs\":"<<inputs
      <<",\"outputs_open\":2,\"format\":17,\"qpc_hz\":"<<hz.QuadPart
      <<",\"input_latency\":"<<inlat<<",\"output_latency\":"<<outlat<<"}";
    std::ofstream raw("callbacks.bin",std::ios::binary);
    size_t written=0;
    auto drain=[&] {
        size_t end=published.load(std::memory_order_acquire);
        if (end>written) {
            raw.write(reinterpret_cast<const char*>(records.data()+written),(end-written)*sizeof(Record));
            raw.flush();
            written=end;
        }
    };
    check(ASIOStart(),"start");
    // Each request comes from the measurement controller, after the old stream's window closes.
    int request=1;
    bool running=true, allocated=true;
    auto require_ok=[](ASIOError status,const char *op) {
        if (status!=ASE_OK) throw std::runtime_error(std::string(op)+" returned "+std::to_string(long(status)));
    };
    const auto deadline=GetTickCount64()+45*60000;
    while (GetFileAttributesW(L"finish")==INVALID_FILE_ATTRIBUTES &&
           GetTickCount64()<deadline && written<capacity && raw) {
        Sleep(100); drain();
        const std::string stem="reopen-"+std::to_string(request);
        std::ifstream trigger(stem+".request");
        std::string mode;
        if (!(trigger>>mode) || (mode!="stream" && mode!="driver")) continue;
        LARGE_INTEGER start_stamp; QueryPerformanceCounter(&start_stamp);
        std::string error;
        try {
            if (running) {
                auto rc=ASIOStop();
                if (mode=="stream") require_ok(rc,"stop");
                running=false; drain();
            }
            if (allocated) {
                auto rc=ASIODisposeBuffers();
                if (mode=="stream") require_ok(rc,"dispose");
                allocated=false;
            }
            if (mode=="driver") {
                require_ok(ASIOExit(),"exit");
                if (!loadAsioDriver(driver)) throw std::runtime_error("reload failed");
                ASIODriverInfo fresh{}; fresh.asioVersion=2; fresh.sysRef=GetDesktopWindow();
                require_ok(ASIOInit(&fresh),"re-init");
                require_ok(ASIOSetSampleRate(rate),"restore sample rate");
            }
            long ins,outs;
            require_ok(ASIOGetChannels(&ins,&outs),"read channels");
            require_ok(ASIOGetSampleRate(&actual),"read rate");
            require_ok(ASIOGetBufferSize(&min,&max,&preferred,&granularity),"read buffer size");
            if (actual!=rate || preferred!=frames || ins!=inputs || outs!=outputs)
                throw std::runtime_error("settings changed");
            for (auto &b:buffers) {
                b.buffers[0]=b.buffers[1]=nullptr;
                ASIOChannelInfo ci{}; ci.isInput=b.isInput; ci.channel=b.channelNum;
                require_ok(ASIOGetChannelInfo(&ci),"channel format");
                if (ci.type!=ASIOSTInt24LSB) throw std::runtime_error("format changed");
            }
            require_ok(ASIOCreateBuffers(buffers.data(),long(buffers.size()),frames,&callbacks),"create");
            allocated=true;
            require_ok(ASIOGetLatencies(&inlat,&outlat),"latencies");
            output_ready=ASIOOutputReady()==ASE_OK;
            require_ok(ASIOStart(),"restart");
            running=true;
        } catch (const std::exception &e) { error=e.what(); }
        LARGE_INTEGER done_stamp; QueryPerformanceCounter(&done_stamp);
        std::ofstream result(stem+".tmp");
        result<<"{\"mode\":\""<<mode<<"\",\"error\":\""<<error<<"\",\"pid\":"<<GetCurrentProcessId()
              <<",\"start_qpc\":"<<start_stamp.QuadPart<<",\"done_qpc\":"<<done_stamp.QuadPart
              <<",\"sample_rate\":"<<actual<<",\"preferred\":"<<preferred<<",\"input_latency\":"<<inlat
              <<",\"output_latency\":"<<outlat<<",\"inputs\":"<<inputs<<",\"outputs_open\":2}";
        result.close();
        if (!MoveFileA((stem+".tmp").c_str(),(stem+".json").c_str())) return 6;
        ++request;
    }
    if (running) check(ASIOStop(),"stop");
    drain(); raw.close();
    ASIOSampleRate ending{}; check(ASIOGetSampleRate(&ending),"final rate");
    check(ASIOGetBufferSize(&min,&max,&preferred,&granularity),"final buffer sizes");
    if (allocated) check(ASIODisposeBuffers(),"dispose");
    ASIOExit();
    std::ofstream("end.json")<<"{\"callbacks\":"<<written<<",\"sample_rate\":"<<ending
      <<",\"preferred\":"<<preferred<<",\"reset_requests\":"<<resets.load()
      <<",\"resync_requests\":"<<resyncs.load()<<",\"rate_notifications\":"<<rates.load()<<"}";
    return written<capacity && raw && GetFileAttributesW(L"finish")!=INVALID_FILE_ATTRIBUTES ? 0 : 4;
}
