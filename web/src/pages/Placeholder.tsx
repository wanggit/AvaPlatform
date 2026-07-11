// 临时占位页面：用于尚未接入正式页面的路由展示。
import { Card, Typography } from 'antd';

const { Title, Paragraph } = Typography;

export default function Placeholder({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <Title level={4}>{title}</Title>
      <Card>
        <Paragraph style={{ marginBottom: 0 }}>{description}</Paragraph>
      </Card>
    </div>
  );
}
