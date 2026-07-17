import Link from 'next/link'
import { Card, Row, Col } from 'antd'
import { FileTextOutlined, SafetyCertificateOutlined, TeamOutlined } from '@ant-design/icons'

export function QualityLanding() {
  return (
    <div>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 24 }}>质量管理</h1>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={8}>
          <Link href="/quality/deviations">
            <Card hoverable>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <FileTextOutlined style={{ fontSize: 32, color: '#1677ff' }} />
                <div>
                  <div style={{ fontSize: 16, fontWeight: 600 }}>偏差管理</div>
                  <div style={{ fontSize: 13, color: '#787671' }}>记录和跟踪生产偏差</div>
                </div>
              </div>
            </Card>
          </Link>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Link href="/quality/capas">
            <Card hoverable>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <SafetyCertificateOutlined style={{ fontSize: 32, color: '#1aae39' }} />
                <div>
                  <div style={{ fontSize: 16, fontWeight: 600 }}>CAPA管理</div>
                  <div style={{ fontSize: 13, color: '#787671' }}>纠正和预防措施</div>
                </div>
              </div>
            </Card>
          </Link>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Link href="/quality/department-contacts">
            <Card hoverable>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <TeamOutlined style={{ fontSize: 32, color: '#7b3ff2' }} />
                <div>
                  <div style={{ fontSize: 16, fontWeight: 600 }}>部门联系人</div>
                  <div style={{ fontSize: 13, color: '#787671' }}>配置部门联系信息</div>
                </div>
              </div>
            </Card>
          </Link>
        </Col>
      </Row>
    </div>
  )
}
