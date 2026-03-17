"use client";

import { Skeleton, Card, Row, Col } from "antd";

export default function DashboardLoading() {
  return (
    <div className="skeleton-page">
      <Skeleton active paragraph={{ rows: 0 }} style={{ marginBottom: 16 }} />
      <Row gutter={[16, 16]}>
        {[1, 2, 3, 4].map((i) => (
          <Col xs={24} sm={12} lg={6} key={i}>
            <Card>
              <Skeleton active paragraph={{ rows: 1 }} />
            </Card>
          </Col>
        ))}
      </Row>
      <Card style={{ marginTop: 24 }}>
        <Skeleton active paragraph={{ rows: 8 }} />
      </Card>
    </div>
  );
}
