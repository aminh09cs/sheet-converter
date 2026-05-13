from __future__ import annotations

from enum import StrEnum


class ProjectType(StrEnum):
    HIGH_RISE = "cao_tang"
    LOW_RISE = "thap_tang"

    @property
    def label(self) -> str:
        return "Cao tầng" if self is ProjectType.HIGH_RISE else "Thấp tầng"


HIGH_RISE_COLUMNS: tuple[str, ...] = (
    "Mã dự án",
    "Mã phân khu",
    "Mã tòa nhà",
    "Loại hình dự án",
    "Mã căn hộ",
    "Tầng số",
    "Mã hướng",
    "Mã trục căn",
    "Số phòng ngủ",
    "Số phòng Wc",
    "Mã loại hình căn hộ",
    "Diện tích tim tường",
    "Diện tích thông thủy",
    "Giá niêm yết",
    "Giá thanh toán sớm",
    "Giá TTTĐ",
    "Giá vay",
    "Giá /m2",
    "Mô tả giá",
    "Đối tác",
    "Nhóm quỹ bán",
    "Đội ngũ bán hàng",
    "Nhân viên bán hàng",
    "Giỏ bank",
    "Quỹ chủ đầu tư",
    "Loại quỹ",
    "Ngày ký TT đặt cọc",
    "Ghi chú",
    "Tiêu chuẩn bàn giao",
    "Mã phiếu tính giá",
    "Link phiếu tính giá",
    "Quà tặng",
    "Ngày hiệu lực",
    "Mô tả CSBH",
    "Link CSBH Full",
    "Link CSBH Tóm tắt",
    "Link layout thiết kế",
    "Link Avatar căn hộ",
    "Trạng thái căn hộ",
)

LOW_RISE_COLUMNS: tuple[str, ...] = (
    "Mã dự án",
    "Mã phân khu",
    "Mã căn hộ",
    "Loại hình dự án",
    "Mã hướng",
    "Mã loại hình căn hộ",
    "Diện tích đất",
    "Diện tích xây dựng",
    "Diện tích tầng 1",
    "Mặt tiền",
    "Ghi chú",
    "Tiêu chuẩn bàn giao",
    "Giá niêm yết",
    "Giá thanh toán sớm",
    "Giá TTTĐ",
    "Giá vay",
    "Giá /m2",
    "Mô tả giá",
    "Nhóm quỹ bán",
    "Đội ngũ bán hàng",
    "Nhân viên bán hàng",
    "Đối tác",
    "Giỏ bank",
    "Quỹ chủ đầu tư",
    "Loại quỹ",
    "Ngày ký TT đặt cọc",
    "Mã phiếu tính giá",
    "Link phiếu tính giá",
    "Quà tặng",
    "Ngày hiệu lực",
    "Mô tả CSBH",
    "Link CSBH Full",
    "Link CSBH Tóm tắt",
    "Link layout thiết kế",
    "Link Avatar căn hộ",
    "Trạng thái căn hộ",
)


def target_columns(project_type: ProjectType) -> tuple[str, ...]:
    match project_type:
        case ProjectType.HIGH_RISE:
            return HIGH_RISE_COLUMNS
        case ProjectType.LOW_RISE:
            return LOW_RISE_COLUMNS
