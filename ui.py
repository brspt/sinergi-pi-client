#!/usr/bin/env python3
"""Sinergi AI — Pi Zero Cloud UI  (PyGame + picamera2 + Cloud Run + Firebase)"""
import base64
import sys
import threading
import time
import uuid
from io import BytesIO

import pygame

from camera import CAPTURE_PATH
from client import send_to_cloud

SCREEN_W = 1024
SCREEN_H = 600
PREV_W   = 750
SB_X     = 754
SB_W     = 270
MAX_SLOTS = 4

# ── Palette ────────────────────────────────────────────────────────────────
C_BG      = (244, 247, 244)
C_WHITE   = (255, 255, 255)
C_GREEN   = (32,  116,  50)
C_BLUE    = (18,   64, 126)
C_LIME    = (42,  136,  56)
C_ORANGE  = (206, 126,   8)
C_GRAY    = ( 96, 108,  98)
C_DGRAY   = ( 46,  52,  46)
C_TEXT    = ( 16,  32,  20)
C_SUB     = ( 72, 100,  78)
C_RED_BG  = (255, 232, 232)
C_RED_FG  = (172,  26,  26)
C_SB_BG   = ( 18,  28,  18)
C_SB_CTRL = ( 34,  48,  34)
C_BORDER  = (200, 214, 202)
C_INSTR   = (220, 238, 220)
C_CLOUD   = ( 40, 120, 200)   # cloud sync indicator

# ── States ─────────────────────────────────────────────────────────────────
MAIN   = "main"
SELECT = "select"
READY  = "ready"
REVIEW = "review"
WORK   = "work"
RESULT = "result"

INSTRUCTIONS = {
    ("hasil_panen", "padi"):    "Arahkan ke 1 rumpun padi dari atas",
    ("hasil_panen", "edamame"): "Arahkan ke 1 pohon edamame",
    ("deteksi_hpt", "padi"):    "Foto tanaman padi yang terindikasi HPT",
    ("deteksi_hpt", "edamame"): "Foto pohon edamame yang terindikasi HPT",
}

# ── Sidebar control rects ─────────────────────────────────────────────────
_SB_BRT_LBL = (SB_X,        69, SB_W, 15)
_SB_BRT_M   = (SB_X,        86,  74,  42)
_SB_BRT_V   = (SB_X +  78,  86, 118,  42)
_SB_BRT_P   = (SB_X + 200,  86,  70,  42)

_SB_SAT_LBL = (SB_X,       138, SB_W, 15)
_SB_SAT_M   = (SB_X,       155,  74,  42)
_SB_SAT_V   = (SB_X +  78, 155, 118,  42)
_SB_SAT_P   = (SB_X + 200, 155,  70,  42)

_SB_FCK_LBL = (SB_X,       207, SB_W, 15)
_SB_FCK_M   = (SB_X,       224,  74,  42)
_SB_FCK_V   = (SB_X +  78, 224, 118,  42)
_SB_FCK_P   = (SB_X + 200, 224,  70,  42)

_SB_SHP_LBL = (SB_X,       276, SB_W, 15)
_SB_SHP_M   = (SB_X,       293,  74,  42)
_SB_SHP_V   = (SB_X +  78, 293, 118,  42)
_SB_SHP_P   = (SB_X + 200, 293,  70,  42)

_SB_CTR_LBL = (SB_X,       345, SB_W, 15)
_SB_CTR_M   = (SB_X,       362,  74,  42)
_SB_CTR_V   = (SB_X +  78, 362, 118,  42)
_SB_CTR_P   = (SB_X + 200, 362,  70,  42)

_SB_AWB_LBL = (SB_X,       414, SB_W, 15)
_SB_AWB_M   = (SB_X,       431,  40,  42)
_SB_AWB_V   = (SB_X +  44, 431, 182,  42)
_SB_AWB_P   = (SB_X + 230, 431,  40,  42)

_SB_FOTO    = (SB_X + 4,   489, SB_W - 8, 62)
_SB_BACK_RD = (SB_X + 4,   557, SB_W - 8, 36)

# ── Main / Select cards ────────────────────────────────────────────────────
_L    = (24,  88, 480, 416)
_R    = (520, 88, 480, 416)
_BACK = (24,  520, 240, 64)

# ── Review ─────────────────────────────────────────────────────────────────
_BTN_ULANG = (24,  492, 454, 84)
_BTN_KIRIM = (546, 492, 454, 84)

# ── Result ─────────────────────────────────────────────────────────────────
_BTN_BACK_RESULT  = (24,  490, 270, 72)
_BTN_NEXT_SLOT    = (548, 490, 225, 72)   # slot berikutnya
_BTN_FINISH       = (548, 490, 225, 72)   # selesai (same pos, different label)
_BTN_FOTO_LAGI    = (738, 490, 262, 72)   # alias

AWB_MODES = [
    ("Auto",        0),
    ("Siang",       4),
    ("Mendung",     5),
    ("Indoor",      3),
    ("Neon/TL",     2),
    ("Lampu Pijar", 1),
]


class App:
    def __init__(self):
        pygame.init()
        pygame.mouse.set_visible(False)
        flags = pygame.FULLSCREEN | pygame.NOFRAME
        try:
            self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
        except Exception:
            self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Sinergi AI")
        self.clock = pygame.time.Clock()

        def font(size, bold=False):
            for name in ("Ubuntu", "DejaVu Sans", "FreeSans", None):
                try:
                    return pygame.font.SysFont(name, size, bold=bold)
                except Exception:
                    continue
            return pygame.font.Font(None, size)

        self.f_title  = font(26, bold=True)
        self.f_card   = font(48, bold=True)
        self.f_sub_c  = font(20)
        self.f_big    = font(38, bold=True)
        self.f_med    = font(30, bold=True)
        self.f_small  = font(22)
        self.f_xs     = font(18)
        self.f_sb     = font(20, bold=True)
        self.f_num    = font(108, bold=True)
        self.f_instr  = font(22)

        # App state
        self.state       = MAIN
        self.mode        = None
        self.plant       = None
        self.result      = None
        self.error       = None
        self.status_msg  = ""
        self.result_img  = None
        self.preview_img = None

        # Session / slot tracking
        self.session_id    = self._new_session()
        self.current_slot  = 1
        self.slot_results  = []     # list of result dicts per slot

        # Live camera
        self.live_surf     = None
        self.live_running  = False
        self.capture_now   = False
        self.capturing     = False

        # Camera controls
        self.cam_brightness     = 0.0
        self.cam_saturation     = 1.0
        self.cam_sharpness      = 1.0
        self.cam_contrast       = 1.0
        self.cam_lens_pos       = 1.0
        self.cam_awb_idx        = 0
        self.cam_controls_dirty = False

    def _new_session(self) -> str:
        return uuid.uuid4().hex[:12].upper()

    # ── main loop ──────────────────────────────────────────────────────────

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self._quit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if not self.capturing and self.state != WORK:
                        self._click(event.pos)
            self._draw()
            pygame.display.flip()
            self.clock.tick(30)

    def _quit(self):
        self.live_running = False
        time.sleep(0.2)
        pygame.quit()
        sys.exit()

    # ── click routing ──────────────────────────────────────────────────────

    def _click(self, pos):
        if self.state == MAIN:
            if _hit(pos, *_L):
                self.mode = "hasil_panen"; self.state = SELECT
            elif _hit(pos, *_R):
                self.mode = "deteksi_hpt"; self.state = SELECT

        elif self.state == SELECT:
            if _hit(pos, *_L):
                self.plant = "padi";    self._start_session()
            elif _hit(pos, *_R):
                self.plant = "edamame"; self._start_session()
            elif _hit(pos, *_BACK):
                self.state = MAIN

        elif self.state == READY:
            if _hit(pos, *_SB_FOTO):
                self._do_capture()
            elif _hit(pos, *_SB_BACK_RD):
                self._exit_ready(); self.state = SELECT
            elif _hit(pos, *_SB_BRT_M):
                self.cam_brightness = max(-1.0, round(self.cam_brightness - 0.1, 1))
                self.cam_controls_dirty = True
            elif _hit(pos, *_SB_BRT_P):
                self.cam_brightness = min(1.0, round(self.cam_brightness + 0.1, 1))
                self.cam_controls_dirty = True
            elif _hit(pos, *_SB_SAT_M):
                self.cam_saturation = max(0.0, round(self.cam_saturation - 0.2, 1))
                self.cam_controls_dirty = True
            elif _hit(pos, *_SB_SAT_P):
                self.cam_saturation = min(4.0, round(self.cam_saturation + 0.2, 1))
                self.cam_controls_dirty = True
            elif _hit(pos, *_SB_FCK_M):
                self.cam_lens_pos = max(0.0, round(self.cam_lens_pos - 0.5, 1))
                self.cam_controls_dirty = True
            elif _hit(pos, *_SB_FCK_P):
                self.cam_lens_pos = min(10.0, round(self.cam_lens_pos + 0.5, 1))
                self.cam_controls_dirty = True
            elif _hit(pos, *_SB_SHP_M):
                self.cam_sharpness = max(0.0, round(self.cam_sharpness - 0.2, 1))
                self.cam_controls_dirty = True
            elif _hit(pos, *_SB_SHP_P):
                self.cam_sharpness = min(4.0, round(self.cam_sharpness + 0.2, 1))
                self.cam_controls_dirty = True
            elif _hit(pos, *_SB_CTR_M):
                self.cam_contrast = max(0.0, round(self.cam_contrast - 0.1, 1))
                self.cam_controls_dirty = True
            elif _hit(pos, *_SB_CTR_P):
                self.cam_contrast = min(4.0, round(self.cam_contrast + 0.1, 1))
                self.cam_controls_dirty = True
            elif _hit(pos, *_SB_AWB_M):
                self.cam_awb_idx = (self.cam_awb_idx - 1) % len(AWB_MODES)
                self.cam_controls_dirty = True
            elif _hit(pos, *_SB_AWB_P):
                self.cam_awb_idx = (self.cam_awb_idx + 1) % len(AWB_MODES)
                self.cam_controls_dirty = True

        elif self.state == REVIEW:
            if _hit(pos, *_BTN_KIRIM):
                self._start_inference()
            elif _hit(pos, *_BTN_ULANG):
                self._enter_ready()

        elif self.state == RESULT:
            if self.error:
                if _hit(pos, *_BTN_BACK_RESULT):
                    self._reset_full()
            else:
                if _hit(pos, *_BTN_BACK_RESULT):
                    self._reset_full()
                elif _hit(pos, *_BTN_NEXT_SLOT):
                    if self.current_slot < MAX_SLOTS:
                        self._next_slot()
                    else:
                        self._finish_session()

    # ── session / slot ─────────────────────────────────────────────────────

    def _start_session(self):
        self.session_id   = self._new_session()
        self.current_slot = 1
        self.slot_results = []
        self._enter_ready()

    def _next_slot(self):
        self.current_slot += 1
        self.result = None; self.error = None; self.result_img = None
        self._enter_ready()

    def _finish_session(self):
        self._reset_full()

    # ── live camera ────────────────────────────────────────────────────────

    def _enter_ready(self):
        self.state          = READY
        self.live_surf      = None
        self.capture_now    = False
        self.capturing      = False
        self.preview_img    = None
        self.cam_controls_dirty = True
        self.live_running   = True
        threading.Thread(target=self._live_worker, daemon=True).start()

    def _exit_ready(self):
        self.live_running = False
        self.live_surf    = None

    def _do_capture(self):
        if not self.capturing:
            self.capturing   = True
            self.capture_now = True

    def _live_worker(self):
        try:
            from picamera2 import Picamera2
            from PIL import Image as PILImage

            cam = Picamera2()
            cam.configure(cam.create_preview_configuration(
                main={"size": (960, 720), "format": "RGB888"}
            ))
            cam.start()
            time.sleep(0.8)

            while self.live_running:
                if self.cam_controls_dirty:
                    try:
                        _, awb_code = AWB_MODES[self.cam_awb_idx]
                        cam.set_controls({
                            "Brightness": float(self.cam_brightness),
                            "Saturation": float(self.cam_saturation),
                            "Sharpness":  float(self.cam_sharpness),
                            "Contrast":   float(self.cam_contrast),
                            "AwbMode":    awb_code,
                        })
                    except Exception:
                        pass
                    try:
                        cam.set_controls({"AfMode": 0, "LensPosition": float(self.cam_lens_pos)})
                    except Exception:
                        pass
                    self.cam_controls_dirty = False

                arr = cam.capture_array("main")
                arr = arr[:, :, ::-1]   # BGR → RGB

                if self.capture_now:
                    PILImage.fromarray(arr).save(CAPTURE_PATH, "JPEG", quality=90)
                    self.capture_now  = False
                    self.live_running = False
                    self.preview_img  = _arr_to_surf(arr, 1010, 426)
                    cam.stop(); cam.close()
                    self.capturing = False
                    self.state     = REVIEW
                    return

                self.live_surf = _arr_to_surf(arr, PREV_W, 540)
                time.sleep(0.04)

            cam.stop()
            cam.close()

        except Exception as exc:
            self.live_running = False
            self.capturing    = False
            self.error        = f"Kamera: {exc}"
            if self.state == READY:
                self.state = RESULT

    # ── inference ──────────────────────────────────────────────────────────

    def _start_inference(self):
        self.state      = WORK
        self.status_msg = "Mengunggah ke Cloud..."
        self.result     = None; self.error = None; self.result_img = None
        threading.Thread(target=self._infer_worker, daemon=True).start()

    def _infer_worker(self):
        try:
            with open(CAPTURE_PATH, "rb") as fh:
                data = fh.read()
            self.status_msg = "Memproses YOLO..."
            res = send_to_cloud(
                self.mode, self.plant, data,
                session_id=self.session_id,
                sample_slot=self.current_slot,
            )
            self.result = res
            self.slot_results.append(res)
            self._load_result_img(res.get("annotated_image_base64", ""))
        except Exception as exc:
            self.error = str(exc)
        self.state = RESULT

    # ── helpers ────────────────────────────────────────────────────────────

    def _load_result_img(self, b64: str):
        if not b64:
            return
        try:
            import numpy as np
            from PIL import Image as PILImage
            pil = PILImage.open(BytesIO(base64.b64decode(b64))).convert("RGB")
            pil.thumbnail((510, 366))
            self.result_img = _arr_to_surf(np.array(pil), 510, 366)
        except Exception:
            self.result_img = None

    def _reset_full(self):
        self._exit_ready()
        self.state = MAIN; self.mode = None; self.plant = None
        self.result = None; self.error = None
        self.result_img = None; self.preview_img = None
        self.current_slot = 1; self.slot_results = []

    # ── drawing ────────────────────────────────────────────────────────────

    def _draw(self):
        self.screen.fill(C_BG)
        pygame.draw.rect(self.screen, C_GREEN, (0, 0, SCREEN_W, 4))
        _txt(self.screen, self.f_title, "SINERGI AI", C_TEXT, (24, 10))
        _txt(self.screen, self.f_xs,    "Cloud Field Tool", C_SUB,  (24, 36))
        # cloud indicator dot
        pygame.draw.circle(self.screen, C_CLOUD, (SCREEN_W - 20, 22), 7)
        _txt(self.screen, self.f_xs, "CLOUD", C_CLOUD, (SCREEN_W - 80, 15))
        pygame.draw.line(self.screen, C_BORDER, (0, 54), (SCREEN_W, 54), 1)
        {
            MAIN:   self._d_main,
            SELECT: self._d_select,
            READY:  self._d_ready,
            WORK:   self._d_loading,
            REVIEW: self._d_review,
            RESULT: self._d_result,
        }[self.state]()

    def _d_main(self):
        _txt(self.screen, self.f_xs, "Pilih jenis analisis:", C_SUB, (24, 64))
        _btn2(self.screen, self.f_card, self.f_sub_c, *_L, C_GREEN,
              "HASIL PANEN", "Hitung malai & polong")
        _btn2(self.screen, self.f_card, self.f_sub_c, *_R, C_BLUE,
              "DETEKSI HPT", "Identifikasi hama & penyakit")

    def _d_select(self):
        lbl = "Hasil Panen" if self.mode == "hasil_panen" else "Deteksi HPT"
        _txt(self.screen, self.f_xs, f"{lbl}  —  Pilih tanaman:", C_SUB, (24, 64))
        _btn2(self.screen, self.f_card, self.f_sub_c, *_L, C_LIME,
              "PADI", "Oryza sativa")
        _btn2(self.screen, self.f_card, self.f_sub_c, *_R, C_ORANGE,
              "EDAMAME", "Glycine max")
        _btn(self.screen, self.f_med, *_BACK, C_GRAY, "< Kembali")

    def _d_ready(self):
        TOP = 58
        if self.live_surf:
            w, h = self.live_surf.get_size()
            self.screen.blit(self.live_surf, ((PREV_W - w) // 2, TOP + (SCREEN_H - TOP - h) // 2))
        else:
            pygame.draw.rect(self.screen, (28, 36, 28), (0, TOP, PREV_W, SCREEN_H - TOP))
            _ctxt(self.screen, self.f_small, "Inisialisasi kamera...", C_SUB,
                  PREV_W // 2, TOP + (SCREEN_H - TOP) // 2)

        # instruction + slot overlay
        instr = INSTRUCTIONS.get((self.mode, self.plant), "Arahkan kamera")
        s = pygame.Surface((PREV_W, 38), pygame.SRCALPHA)
        s.fill((0, 0, 0, 160))
        self.screen.blit(s, (0, TOP))
        slot_txt = f"Slot {self.current_slot}/{MAX_SLOTS}"
        _txt(self.screen, self.f_xs, slot_txt, (180, 220, 120), (8, TOP + 12))
        _ctxt(self.screen, self.f_instr, instr, C_INSTR, PREV_W // 2 + 30, TOP + 19)

        if self.capturing:
            ov = pygame.Surface((PREV_W, SCREEN_H - TOP), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 170))
            self.screen.blit(ov, (0, TOP))
            _ctxt(self.screen, self.f_big, "Mengambil foto...", C_INSTR,
                  PREV_W // 2, TOP + (SCREEN_H - TOP) // 2)

        # sidebar
        pygame.draw.rect(self.screen, C_SB_BG, (SB_X, TOP, SB_W, SCREEN_H - TOP))

        def sb_ctrl(lbl_r, m_r, v_r, p_r, label, value):
            _ctxt(self.screen, self.f_xs, label, (160, 200, 160),
                  SB_X + SB_W // 2, lbl_r[1] + 7)
            _btn(self.screen, self.f_sb, *m_r, C_SB_CTRL, "−", radius=8)
            _sb_val(self.screen, self.f_sb, v_r, value)
            _btn(self.screen, self.f_sb, *p_r, C_SB_CTRL, "+", radius=8)

        sb_ctrl(_SB_BRT_LBL, _SB_BRT_M, _SB_BRT_V, _SB_BRT_P,
                "KECERAHAN", f"{self.cam_brightness:+.1f}")
        sb_ctrl(_SB_SAT_LBL, _SB_SAT_M, _SB_SAT_V, _SB_SAT_P,
                "SATURASI",  f"{self.cam_saturation:.1f}")
        sb_ctrl(_SB_FCK_LBL, _SB_FCK_M, _SB_FCK_V, _SB_FCK_P,
                "FOKUS",     f"{self.cam_lens_pos:.1f}")
        sb_ctrl(_SB_SHP_LBL, _SB_SHP_M, _SB_SHP_V, _SB_SHP_P,
                "KETAJAMAN", f"{self.cam_sharpness:.1f}")
        sb_ctrl(_SB_CTR_LBL, _SB_CTR_M, _SB_CTR_V, _SB_CTR_P,
                "KONTRAS",   f"{self.cam_contrast:.1f}")

        _ctxt(self.screen, self.f_xs, "WHITE BALANCE", (160, 200, 160),
              SB_X + SB_W // 2, _SB_AWB_LBL[1] + 7)
        _btn(self.screen, self.f_sb, *_SB_AWB_M, C_SB_CTRL, "<", radius=8)
        _sb_val(self.screen, self.f_xs, _SB_AWB_V, AWB_MODES[self.cam_awb_idx][0])
        _btn(self.screen, self.f_sb, *_SB_AWB_P, C_SB_CTRL, ">", radius=8)

        if not self.capturing:
            _btn(self.screen, self.f_med, *_SB_FOTO,    C_GREEN, "FOTO")
            _btn(self.screen, self.f_xs,  *_SB_BACK_RD, C_DGRAY, "< Kembali")

    def _d_loading(self):
        tick = (pygame.time.get_ticks() // 400) % 4
        surf = self.f_big.render(self.status_msg + "." * (tick + 1), True, C_TEXT)
        self.screen.blit(surf, surf.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 24)))
        hint = self.f_small.render("Harap tunggu...", True, C_SUB)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 36)))

    def _d_review(self):
        if self.preview_img:
            w, h = self.preview_img.get_size()
            self.screen.blit(self.preview_img, ((SCREEN_W - w) // 2, 60))
        else:
            pygame.draw.rect(self.screen, (230, 235, 230), (12, 60, SCREEN_W - 24, 420), border_radius=12)
            _ctxt(self.screen, self.f_small, "Tidak ada preview", C_SUB, SCREEN_W // 2, 270)
        slot_info = f"Slot {self.current_slot}/{MAX_SLOTS}"
        _txt(self.screen, self.f_xs, slot_info, C_SUB, (24, 488))
        _btn(self.screen, self.f_med,  *_BTN_ULANG, C_ORANGE, "FOTO ULANG")
        _btn(self.screen, self.f_card, *_BTN_KIRIM, C_GREEN,  "KIRIM  ☁")

    def _d_result(self):
        pl = "Padi" if self.plant == "padi" else "Edamame"
        mo = "Hasil Panen" if self.mode == "hasil_panen" else "Deteksi HPT"
        slot_str = f"Slot {self.current_slot}/{MAX_SLOTS}"
        _txt(self.screen, self.f_xs, f"{pl}  —  {mo}  ·  {slot_str}", C_SUB, (24, 62))

        if self.error:
            pygame.draw.rect(self.screen, C_RED_BG, (24, 82, SCREEN_W - 48, 110), border_radius=14)
            _ctxt(self.screen, self.f_small, f"Error: {self.error[:80]}", C_RED_FG, SCREEN_W // 2, 137)

        elif self.result:
            count  = self.result.get("count", 0)
            clabel = "malai terdeteksi" if self.mode == "hasil_panen" else "HPT terdeteksi"
            doc_id = self.result.get("doc_id", "")

            _card(self.screen, 24, 82, 430, 380)
            num = self.f_num.render(str(count), True, C_GREEN)
            self.screen.blit(num, num.get_rect(center=(239, 195)))
            lab = self.f_small.render(clabel, True, C_SUB)
            self.screen.blit(lab, lab.get_rect(center=(239, 272)))

            # slot progress dots
            dot_y = 308
            for i in range(MAX_SLOTS):
                cx = 239 - (MAX_SLOTS - 1) * 18 + i * 36
                filled = i < self.current_slot
                pygame.draw.circle(self.screen, C_GREEN if filled else C_BORDER, (cx, dot_y), 10)
                if filled:
                    pygame.draw.circle(self.screen, C_WHITE, (cx, dot_y), 5)

            # cloud saved indicator
            if doc_id:
                _ctxt(self.screen, self.f_xs, f"✓ Tersimpan di cloud", C_CLOUD, 239, 340)
                _ctxt(self.screen, self.f_xs, doc_id, (130, 160, 130), 239, 360)

            cc = self.result.get("class_counts", {})
            if len(cc) > 1:
                y_cc = 375
                for cls, cnt in list(cc.items())[:3]:
                    row = self.f_xs.render(f"  {cls.replace('_',' ').title()}: {cnt}", True, C_SUB)
                    self.screen.blit(row, (44, y_cc)); y_cc += 22

            _card(self.screen, 468, 82, 532, 380, color=C_BG)
            if self.result_img:
                iw, ih = self.result_img.get_size()
                self.screen.blit(self.result_img, (468 + (532 - iw) // 2, 82 + (380 - ih) // 2))

        # buttons
        _btn(self.screen, self.f_med, *_BTN_BACK_RESULT, C_GRAY, "< Menu")
        if not self.error:
            if self.current_slot < MAX_SLOTS:
                _btn(self.screen, self.f_med, *_BTN_NEXT_SLOT, C_GREEN, f"Slot {self.current_slot + 1} →")
            else:
                _btn(self.screen, self.f_med, *_BTN_FINISH, C_LIME, "Selesai ✓")


# ── util ─────────────────────────────────────────────────────────────────────

def _arr_to_surf(arr, max_w, max_h):
    h, w = arr.shape[:2]
    scale = min(max_w / w, max_h / h, 1.0)
    nw, nh = int(w * scale), int(h * scale)
    surf = pygame.surfarray.make_surface(arr.swapaxes(0, 1))
    if (nw, nh) != (w, h):
        surf = pygame.transform.smoothscale(surf, (nw, nh))
    return surf


def _card(surf, x, y, w, h, color=None, radius=14):
    c = color or C_WHITE
    pygame.draw.rect(surf, C_BORDER, (x + 2, y + 3, w, h), border_radius=radius)
    pygame.draw.rect(surf, c,        (x,     y,     w, h), border_radius=radius)
    pygame.draw.rect(surf, C_BORDER, (x,     y,     w, h), 1, border_radius=radius)


def _sb_val(surf, font, rect, text):
    x, y, w, h = rect
    pygame.draw.rect(surf, (44, 60, 44), (x, y, w, h), border_radius=6)
    _ctxt(surf, font, text, C_INSTR, x + w // 2, y + h // 2)


def _btn(surf, font, x, y, w, h, color, text, radius=12):
    shadow = tuple(max(c - 40, 0) for c in color)
    pygame.draw.rect(surf, shadow, (x + 3, y + 4, w, h), border_radius=radius)
    pygame.draw.rect(surf, color,  (x,     y,     w, h), border_radius=radius)
    surf.blit(font.render(text, True, C_WHITE),
              font.render(text, True, C_WHITE).get_rect(center=(x + w // 2, y + h // 2)))


def _btn2(surf, f_title, f_sub, x, y, w, h, color, title, subtitle=None, radius=14):
    shadow = tuple(max(c - 40, 0) for c in color)
    pygame.draw.rect(surf, shadow, (x + 3, y + 4, w, h), border_radius=radius)
    pygame.draw.rect(surf, color,  (x,     y,     w, h), border_radius=radius)
    if subtitle:
        cy = y + h // 2 - 22
        r = f_title.render(title, True, C_WHITE)
        surf.blit(r, r.get_rect(center=(x + w // 2, cy)))
        rs = f_sub.render(subtitle, True, (210, 235, 215))
        surf.blit(rs, rs.get_rect(center=(x + w // 2, cy + 56)))
    else:
        r = f_title.render(title, True, C_WHITE)
        surf.blit(r, r.get_rect(center=(x + w // 2, y + h // 2)))


def _hit(pos, x, y, w, h):
    return x <= pos[0] <= x + w and y <= pos[1] <= y + h


def _txt(surf, font, text, color, pos):
    surf.blit(font.render(text, True, color), pos)


def _ctxt(surf, font, text, color, cx, cy):
    r = font.render(text, True, color)
    surf.blit(r, r.get_rect(center=(cx, cy)))


if __name__ == "__main__":
    App().run()
