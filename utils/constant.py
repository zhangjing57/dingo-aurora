# 常量的类

# excel的目录文件
EXCEL_TEMP_DIR = "/home/dingoops/temp_excel/"
# 资产模板文件
ASSET_TEMPLATE_FILE_DIR = "/api/template/asset_template.xlsx"

# 资产设备状态 0：空闲、1：备机、2：分配、3：故障
asset_status_dict = ([(0, "空闲"), (0, "备机"), (2, "分配"), (3, "故障")])

# 资产设备模板字段列
asset_equipment_columns =("机架","机柜","U位","设备名称","设备型号","资产编号","序列号","部门","负责人","主机名","IP","IDRAC","用途","密码","操作系统","购买日期","厂商","批次","备注")
# 资产设备基础信息列名对应表的列
asset_basic_info_columns = dict([("asset_name", "设备名称"),("equipment_number", "设备型号"),("sn_number", "序列号"),("asset_number", "资产编号"),("asset_description", "备注")])
# 资产设备厂商信息列名对应表的列
asset_manufacture_info_columns = dict([("name", "厂商")])
# 资产设备位置信息列名对应表的列
asset_position_info_columns = dict([("frame_position", "机架"),("cabinet_position", "机柜"),("u_position", "U位")])
# 资产设备合同信息列名对应表的列
asset_contract_info_columns = dict([("contract_number", "合同号"),("purchase_date", "购买日期"),("batch_number", "批次")])
# 资产设备归属信息列名对应表的列
asset_belong_info_columns = dict([("department_name", "部门"),("user_name", "负责人")])
# 资产设备租户信息列名对应表的列
asset_customer_info_columns = dict([("customer_name", "客户信息"),("rental_duration", "出租时长")])
