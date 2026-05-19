[English](./README.md) | [Tiếng Việt](./README-vi.md) | [中文](./README-zh.md) | [日本語](./README-ja.md)
# Học Claude Code -- Kỹ thuật Harness cho các Agent Thực thụ
<a href="https://trendshift.io/repositories/19746" target="_blank"><img src="https://trendshift.io/api/badge/repositories/19746" alt="shareAI-lab%2Flearn-claude-code | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>
## Agency đến từ Mô hình. Một sản phẩm Agent = Mô hình + Harness.

Trước khi nói về mã nguồn, hãy làm rõ một điều.

**Agency (Khả năng tự trị) -- khả năng nhận thức, suy luận và hành động -- đến từ việc huấn luyện mô hình, chứ không phải từ sự điều phối mã nguồn bên ngoài.** Nhưng một sản phẩm agent hoạt động được cần cả mô hình và harness. Mô hình là người lái xe, harness là phương tiện. Repo này dạy bạn cách chế tạo phương tiện đó.

### Agency đến từ đâu

Cốt lõi của mọi agent là một mạng thần kinh -- một Transformer, một RNN, một hàm học được -- đã được huấn luyện thông qua hàng tỷ lần cập nhật gradient trên dữ liệu chuỗi hành động, để nhận thức môi trường, suy luận về mục tiêu và thực hiện hành động. Agency không bao giờ được ban tặng bởi mã nguồn xung quanh. Nó được mô hình học hỏi trong quá trình huấn luyện.

Con người là ví dụ điển hình nhất. Một mạng thần kinh sinh học được định hình bởi hàng triệu năm huấn luyện tiến hóa, nhận thức thế giới qua các giác quan, suy luận qua bộ não, hành động qua cơ thể. Khi DeepMind, OpenAI hoặc Anthropic nói "agent", ý nghĩa cốt lõi của họ luôn là một thứ: **một mô hình đã học cách hành động, cộng với cơ sở hạ tầng cho phép nó hoạt động trong một môi trường cụ thể.**

Bằng chứng đã được ghi lại trong lịch sử:

- **2013 -- DeepMind DQN chơi Atari.** Một mạng thần kinh duy nhất, chỉ nhận các pixel thô và điểm số trò chơi, đã học cách chơi 7 trò chơi Atari 2600 -- vượt qua tất cả các thuật toán trước đó và đánh bại các chuyên gia con người trong 3 trò chơi. Đến năm 2015, cùng một kiến trúc đó đã mở rộng lên [49 trò chơi và tương đương với những người thử nghiệm con người chuyên nghiệp](https://www.nature.com/articles/nature14236), được công bố trên *Nature*. Không có quy tắc cụ thể cho trò chơi. Không có cây quyết định. Một mô hình, học hỏi từ kinh nghiệm. Mô hình đó chính là agent.

- **2019 -- OpenAI Five chinh phục Dota 2.** Năm mạng thần kinh, sau khi chơi [45.000 năm Dota 2](https://openai.com/index/openai-five-defeats-dota-2-world-champions/) chống lại chính chúng trong 10 tháng, đã đánh bại **OG** -- nhà đương kim vô địch thế giới TI8 -- với tỷ số 2-0 trong một buổi phát trực tiếp tại San Francisco. Trong một đấu trường công cộng sau đó, AI đã thắng 99,4% trong số 42.729 trận đấu với tất cả đối thủ. Không có chiến lược được lập trình sẵn. Không có sự phối hợp nhóm được lập trình siêu cấp. Các mô hình đã học được tinh thần đồng đội, chiến thuật và khả năng thích ứng thời gian thực hoàn toàn thông qua việc tự chơi.

- **2019 -- DeepMind AlphaStar làm chủ StarCraft II.** AlphaStar [đã đánh bại các game thủ chuyên nghiệp với tỷ số 10-1](https://deepmind.google/blog/alphastar-mastering-the-real-time-strategy-game-starcraft-ii/) trong một trận đấu kín, và sau đó đạt được [cấp độ Grandmaster](https://www.nature.com/articles/d41586-019-03298-6) trên các máy chủ châu Âu -- top 0,15% trong số 90.000 người chơi. Một trò chơi với thông tin không hoàn hảo, các quyết định thời gian thực và không gian hành động tổ hợp khổng lồ vượt xa cờ vua và cờ vây. Agent đó là gì? Một mô hình. Được huấn luyện. Không phải được lập trình.

- **2019 -- Tencent Jueyu thống trị Honor of Kings.** "Jueyu" của Tencent AI Lab [đã đánh bại các tuyển thủ chuyên nghiệp KPL](https://www.jiemian.com/article/3371171.html) trong một trận đấu 5v5 đầy đủ tại World Champion Cup. Ở chế độ 1v1, các chuyên gia chỉ thắng được [1 trên 15 trận và không bao giờ trụ được quá 8 phút](https://developer.aliyun.com/article/851058). Cường độ huấn luyện: một ngày tương đương với 440 năm của con người. Đến năm 2021, Jueyu đã vượt qua các tuyển thủ chuyên nghiệp KPL trên toàn bộ các vị trí tướng. Không có bảng đối đầu được xây dựng thủ công. Không có đội hình được lập trình sẵn. Một mô hình đã học toàn bộ trò chơi từ đầu thông qua việc tự chơi.

- **2024-2025 -- Các LLM agent định hình lại kỹ thuật phần mềm.** Claude, GPT, Gemini -- các mô hình ngôn ngữ lớn được huấn luyện trên toàn bộ mã nguồn và suy luận của con người -- đang được triển khai dưới dạng các coding agent. Chúng đọc kho mã nguồn, viết các bản thực thi, gỡ lỗi thất bại, phối hợp trong các nhóm. Kiến trúc này giống hệt với mọi agent trước đó: một mô hình đã được huấn luyện, được đặt vào một môi trường, được cung cấp các công cụ để nhận thức và hành động. Sự khác biệt duy nhất là quy mô của những gì chúng đã học và tính tổng quát của các nhiệm vụ mà chúng giải quyết.

Mỗi cột mốc này đều chỉ ra cùng một sự thật: **agency (khả năng tự trị) -- khả năng nhận thức, suy luận và hành động -- được huấn luyện, không phải được lập trình.** Nhưng mọi agent cũng cần một môi trường để hoạt động: trình giả lập Atari, client Dota 2, engine StarCraft II, IDE và terminal. Mô hình cung cấp trí thông minh. Môi trường cung cấp không gian hành động. Cùng nhau, chúng tạo thành một agent hoàn chỉnh.

### Agent KHÔNG phải là gì

Từ "agent" đã bị chiếm đoạt bởi cả một ngành công nghiệp "đặt ống dẫn prompt" (prompt plumbing).

Các trình xây dựng quy trình kéo thả. Các nền tảng "AI agent" không cần mã nguồn (no-code). Các thư viện điều phối chuỗi prompt. Tất cả chúng đều có chung một ảo tưởng: rằng việc kết nối các lệnh gọi API LLM với các nhánh if-else, đồ thị nút và logic định tuyến được mã hóa cứng cấu thành nên việc "xây dựng một agent".

Không phải vậy. Những gì họ xây dựng là một cỗ máy Rube Goldberg -- một đường ống các quy tắc thủ tục quá phức tạp và mỏng manh, với một LLM được chèn vào như một nút hoàn thiện văn bản được tôn vinh. Đó không phải là một agent. Đó là một shell script với ảo tưởng về sự vĩ đại.

**Các "agent" đặt ống dẫn prompt là ảo tưởng của các lập trình viên không huấn luyện mô hình.** Họ cố gắng dùng vũ lực để tạo ra trí thông minh bằng cách xếp chồng logic thủ tục -- các cây quy tắc khổng lồ, đồ thị nút, các thác chuỗi prompt -- và cầu nguyện rằng đủ mã kết nối sẽ bằng cách nào đó tạo ra hành vi tự trị một cách tự nhiên. Sẽ không có chuyện đó đâu. Bạn không thể dùng kỹ thuật để tạo ra agency. Agency được học, không phải được lập trình.

Những hệ thống đó vừa ra đời đã thất bại: mỏng manh, không thể mở rộng, về cơ bản không có khả năng tổng quát hóa. Chúng là sự hồi sinh hiện đại của GOFAI (Trí tuệ nhân tạo kiểu cũ tốt đẹp) -- các hệ thống quy tắc biểu tượng mà lĩnh vực này đã từ bỏ từ nhiều thập kỷ trước, nay được sơn phết bằng một lớp vỏ LLM. Bao bì khác nhau, nhưng cùng một ngõ cụt.

### Sự thay đổi tư duy: Từ "Phát triển Agent" sang Phát triển Harness

Khi ai đó nói "Tôi đang phát triển một agent", họ chỉ có thể có ý muốn nói một trong hai điều:

**1. Huấn luyện mô hình.** Điều chỉnh trọng số thông qua học tăng cường (reinforcement learning), tinh chỉnh (fine-tuning), RLHF, hoặc các phương pháp dựa trên gradient khác. Thu thập dữ liệu quá trình thực hiện nhiệm vụ -- các chuỗi nhận thức, suy luận và hành động thực tế trong các lĩnh vực thực -- và sử dụng nó để định hình hành vi của mô hình. Đây là những gì DeepMind, OpenAI, Tencent AI Lab và Anthropic làm. Đây là phát triển agent theo đúng nghĩa nhất.

**2. Xây dựng Harness.** Viết mã nguồn cung cấp cho mô hình một môi trường để hoạt động. Đây là những gì hầu hết chúng ta làm, và nó là trọng tâm của kho lưu trữ này.

Một harness là tất cả những gì agent cần để hoạt động trong một lĩnh vực cụ thể:

```
Harness = Công cụ + Kiến thức + Quan sát + Giao diện Hành động + Quyền hạn

    Công cụ:         vào/ra tệp, shell, mạng, cơ sở dữ liệu, trình duyệt
    Kiến thức:       tài liệu sản phẩm, tài liệu tham khảo lĩnh vực, thông số API, hướng dẫn phong cách
    Quan sát:        git diff, nhật ký lỗi, trạng thái trình duyệt, dữ liệu cảm biến
    Hành động:       lệnh CLI, gọi API, tương tác UI
    Quyền hạn:       sandbox, quy trình phê duyệt, ranh giới tin cậy
```

Mô hình quyết định. Harness thực thi. Mô hình suy luận. Harness cung cấp ngữ cảnh. Mô hình là người lái xe. Harness là phương tiện.

**Harness của một coding agent là IDE, terminal và quyền truy cập hệ thống tệp của nó.** Harness của một agent nông nghiệp là mảng cảm biến, bộ điều khiển tưới tiêu và nguồn cấp dữ liệu thời tiết. Harness của một agent khách sạn là hệ thống đặt phòng, các kênh liên lạc với khách và các API quản lý cơ sở vật chất. Agent -- trí thông minh, người đưa ra quyết định -- luôn là mô hình. Harness thay đổi theo từng lĩnh vực. Agent tổng quát hóa trên chúng.

Repo này dạy bạn chế tạo các phương tiện. Phương tiện cho việc lập trình. Nhưng các mẫu thiết kế có thể tổng quát hóa cho bất kỳ lĩnh vực nào: quản lý trang trại, vận hành khách sạn, sản xuất, hậu cần, y tế, giáo dục, nghiên cứu khoa học. Bất cứ nơi nào một nhiệm vụ cần được nhận thức, suy luận và thực hiện -- một agent đều cần một harness.

### Kỹ sư Harness thực sự làm gì

Nếu bạn đang đọc kho lưu trữ này, bạn có thể là một kỹ sư harness -- và đó là một vai trò đầy quyền năng. Đây là công việc thực sự của bạn:

- **Thực thi công cụ.** Trao cho agent đôi tay. Đọc/ghi tệp, thực thi shell, gọi API, điều khiển trình duyệt, truy vấn cơ sở dữ liệu. Mỗi công cụ là một hành động mà agent có thể thực hiện trong môi trường của nó. Hãy thiết kế chúng có tính nguyên tử, có thể kết hợp và được mô tả rõ ràng.

- **Sàng lọc kiến thức.** Cung cấp cho agent chuyên môn trong lĩnh vực. Tài liệu sản phẩm, hồ sơ quyết định kiến trúc, hướng dẫn phong cách, các yêu cầu quy định. Tải chúng theo yêu cầu (s05), không phải tải trước toàn bộ. Agent nên biết những gì có sẵn và lấy những gì nó cần.

- **Quản lý ngữ cảnh.** Cung cấp cho agent một bộ nhớ sạch sẽ. Sự cô lập subagent (s04) ngăn chặn nhiễu bị ròỉ. Nén ngữ cảnh (s06) ngăn chặn lịch sử làm quá tải bộ nhớ. Hệ thống nhiệm vụ (s07) duy trì các mục tiêu vượt ra ngoài bất kỳ cuộc hội thoại đơn lẻ nào.

- **Kiểm soát quyền hạn.** Đặt ra các ranh giới cho agent. Sandbox quyền truy cập tệp. Yêu cầu phê duyệt cho các hoạt động mang tính phá hủy. Thực thi các ranh giới tin cậy giữa agent và các hệ thống bên ngoài. Đây là nơi kỹ thuật an toàn gặp gỡ kỹ thuật harness.

- **Thu thập dữ liệu quá trình thực hiện nhiệm vụ.** Mọi chuỗi hành động mà agent thực hiện trong harness của bạn đều là tín hiệu huấn luyện. Các dấu vết nhận thức-suy luận-hành động từ các lần triển khai thực tế là nguyên liệu thô để tinh chỉnh thế hệ mô hình agent tiếp theo. Harness của bạn không chỉ phục vụ agent -- nó còn có thể giúp cải thiện agent.

Bạn không viết ra trí thông minh. Bạn đang xây dựng thế giới mà trí thông minh đó cư ngụ. Chất lượng của thế giới đó -- agent có thể nhận thức rõ ràng đến mức nào, nó có thể hành động chính xác đến mức nào, kiến thức có sẵn của nó phong phú đến mức nào -- trực tiếp quyết định mức độ hiệu quả mà trí thông minh có thể thể hiện chính nó.

**Hãy xây dựng những bộ harness tuyệt vời. Agent sẽ làm phần còn lại.**

### Tại sao là Claude Code -- Một bài học mẫu mực về Kỹ thuật Harness

Tại sao kho lưu trữ này mổ xẻ cụ thể Claude Code?

Bởi vì Claude Code là bộ harness agent thanh lịch và hoàn thiện nhất mà chúng tôi từng thấy. Không phải vì bất kỳ một thủ thuật thông minh đơn lẻ nào, mà vì những gì nó *không* làm: nó không cố gắng trở thành agent. Nó không áp đặt các quy trình làm việc cứng nhắc. Nó không đoán trước mô hình bằng các cây quyết định phức tạp. Nó cung cấp cho mô hình các công cụ, kiến thức, quản lý ngữ cảnh và ranh giới quyền hạn -- sau đó lùi lại phía sau.

Hãy nhìn vào bản chất thực sự của Claude Code khi được lột bỏ những phần phụ trợ:

```
Claude Code = một vòng lặp agent
            + công cụ (bash, read, write, edit, glob, grep, trình duyệt...)
            + tải kỹ năng theo yêu cầu
            + nén ngữ cảnh
            + tạo subagent
            + hệ thống nhiệm vụ với đồ thị phụ thuộc
            + phối hợp nhóm với hộp thư không đồng bộ
            + cô lập worktree để thực thi song song
            + quản trị quyền hạn
```

Chỉ có vậy. Đó là toàn bộ kiến trúc. Mỗi thành phần là một cơ chế harness -- một phần của thế giới được xây dựng để agent cư ngụ. Bản thân agent? Đó là Claude. Một mô hình. Được Anthropic huấn luyện trên toàn bộ phạm vi suy luận và mã nguồn của con người. Harness không làm cho Claude thông minh. Claude đã thông minh sẵn rồi. Harness trao cho Claude đôi tay, đôi mắt và một không gian làm việc.

Đây là lý do tại sao Claude Code là đối tượng giảng dạy lý tưởng: **nó chứng minh điều gì sẽ xảy ra khi bạn tin tưởng vào mô hình và tập trung kỹ thuật của mình vào harness.** Mỗi phiên học trong kho lưu trữ này (s01-s12) thực hiện kỹ thuật đảo ngược một cơ chế harness từ kiến trúc của Claude Code. Cuối cùng, bạn không chỉ hiểu cách Claude Code hoạt động mà còn hiểu các nguyên tắc phổ quát của kỹ thuật harness áp dụng cho bất kỳ agent nào trong bất kỳ lĩnh vực nào.

Bài học không phải là "sao chép Claude Code". Bài học là: **các sản phẩm agent tốt nhất được xây dựng bởi các kỹ sư hiểu rằng công việc của họ là harness, không phải trí thông minh.**

---

## Tầm nhìn: Lấp đầy vũ trụ bằng các Agent thực thụ

Điều này không chỉ dành cho các coding agent.

Mọi lĩnh vực mà con người thực hiện các công việc phức tạp, nhiều bước, đòi hỏi sự đánh giá chuyên sâu đều là lĩnh vực mà các agent có thể hoạt động -- nếu có bộ harness phù hợp. Các mẫu trong kho lưu trữ này mang tính phổ quát:

```
Agent quản lý bất động sản = mô hình + cảm biến tài sản + công cụ bảo trì + liên lạc với người thuê
Agent nông nghiệp          = mô hình + dữ liệu đất/thời tiết + điều khiển tưới tiêu + kiến thức cây trồng
Agent vận hành khách sạn   = mô hình + hệ thống đặt phòng + các kênh liên lạc khách + API cơ sở vật chất
Agent nghiên cứu y tế      = mô hình + tìm kiếm tài liệu + dụng cụ phòng thí nghiệm + tài liệu quy trình
Agent sản xuất             = mô hình + cảm biến dây chuyền sản xuất + kiểm soát chất lượng + hậu cần
Agent giáo dục             = mô hình + kiến thức chương trình học + tiến độ học sinh + công cụ đánh giá
```

Vòng lặp luôn giống nhau. Các công cụ thay đổi. Kiến thức thay đổi. Quyền hạn thay đổi. Agent -- mô hình -- tổng quát hóa.

Mọi kỹ sư harness khi đọc kho lưu trữ này đang học các mẫu áp dụng xa hơn cả kỹ thuật phần mềm. Bạn đang học cách xây dựng cơ sở hạ tầng cho một tương lai thông minh, tự động. Mỗi bộ harness được thiết kế tốt được triển khai trong một lĩnh vực thực tế là một nơi nữa mà một agent có thể nhận thức, suy luận và hành động.

Đầu tiên chúng ta lấp đầy các xưởng làm việc. Sau đó là các trang trại, bệnh viện, nhà máy. Sau đó là các thành phố. Sau đó là hành tinh.

**Bash là tất cả những gì bạn cần. Agent thực thụ là tất cả những gì vũ trụ cần.**

---

```
                    MÔ HÌNH AGENT
                    =============

    Người dùng --> messages[] --> LLM --> phản hồi
                                          |
                                 stop_reason == "tool_use"?
                               /                          \
                             có                            không
                              |                             |
                        thực thi công cụ              trả về văn bản
                        thêm kết quả vào
                        vòng lặp quay lại ---------> messages[]


    Đó là vòng lặp tối thiểu. Mọi agent AI đều cần vòng lặp này.
    MÔ HÌNH quyết định khi nào gọi công cụ và khi nào dừng lại.
    MÃ NGUỒN chỉ thực thi những gì mô hình yêu cầu.
    Repo này dạy bạn xây dựng những gì bao quanh vòng lặp này --
    harness giúp agent hoạt động hiệu quả trong một lĩnh vực cụ thể.
```

**12 phiên học lũy tiến, từ một vòng lặp đơn giản đến thực thi tự trị độc lập.**
**Mỗi phiên thêm một cơ chế harness. Mỗi cơ chế có một phương châm.**

> **s01** &nbsp; *"Một vòng lặp & Bash là tất cả những gì bạn cần"* &mdash; một công cụ + một vòng lặp = một agent
>
> **s02** &nbsp; *"Thêm một công cụ nghĩa là thêm một trình xử lý"* &mdash; vòng lặp giữ nguyên; công cụ mới đăng ký vào bản đồ điều phối
>
> **s03** &nbsp; *"Một agent không có kế hoạch sẽ bị mất phương hướng"* &mdash; liệt kê các bước trước, sau đó thực thi; tỷ lệ hoàn thành tăng gấp đôi
>
> **s04** &nbsp; *"Chia nhỏ các nhiệm vụ lớn; mỗi nhiệm vụ con nhận một ngữ cảnh sạch"* &mdash; các subagent sử dụng messages[] độc lập, giữ cho cuộc hội thoại chính luôn sạch sẽ
>
> **s05** &nbsp; *"Tải kiến thức khi cần, không phải tải trước"* &mdash; đưa vào thông qua tool_result, không phải qua system prompt
>
> **s06** &nbsp; *"Ngữ cảnh sẽ đầy; bạn cần một cách để tạo chỗ trống"* &mdash; chiến lược nén ba lớp cho các phiên học vô tận
>
> **s07** &nbsp; *"Chia nhỏ mục tiêu lớn thành các nhiệm vụ nhỏ, sắp xếp chúng, lưu vào đĩa"* &mdash; một đồ thị nhiệm vụ dựa trên tệp với các mối phụ thuộc, đặt nền móng cho sự cộng tác đa agent
>
> **s08** &nbsp; *"Chạy các thao tác chậm ở chế độ nền; agent tiếp tục suy nghĩ"* &mdash; các luồng daemon chạy lệnh, đưa ra thông báo khi hoàn thành
>
> **s09** &nbsp; *"Khi nhiệm vụ quá lớn cho một người, hãy ủy thác cho đồng đội"* &mdash; các đồng đội thường trực + hộp thư JSONL
>
> **s10** &nbsp; *"Đồng đội cần các quy tắc giao tiếp chung"* &mdash; một mô hình yêu cầu-phản hồi thúc đẩy mọi cuộc đàm phán
>
> **s11** &nbsp; *"Đồng đội quét bảng nhiệm vụ và tự nhận nhiệm vụ"* &mdash; không cần trưởng nhóm phải chỉ định từng cái một
>
> **s12** &nbsp; *"Mỗi người làm việc trong thư mục riêng của mình, không can thiệp lẫn nhau"* &mdash; các nhiệm vụ quản lý mục tiêu, worktree quản lý thư mục, được liên kết bằng ID

---

## Mẫu cốt lõi

```python
def agent_loop(messages):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM,
            messages=messages, tools=TOOLS,
        )
        messages.append({"role": "assistant",
                         "content": response.content})

        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = TOOL_HANDLERS[block.name](**block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        messages.append({"role": "user", "content": results})
```

Mỗi phiên học chồng một cơ chế harness lên trên vòng lặp này -- mà không làm thay đổi bản thân vòng lặp. Vòng lặp thuộc về agent. Các cơ chế thuộc về harness.

## Phạm vi (Quan trọng)

Kho lưu trữ này là một dự án học tập từ 0 đến 1 cho kỹ thuật harness -- xây dựng môi trường bao quanh một mô hình agent.
Nó cố tình đơn giản hóa hoặc bỏ qua một số cơ chế sản xuất:

- Các bus sự kiện/hook đầy đủ (ví dụ: PreToolUse, SessionStart/End, ConfigChange).
  s12 chỉ bao gồm một luồng sự kiện vòng đời tối thiểu chỉ-thêm (append-only) để phục vụ giảng dạy.
- Quản trị quyền hạn dựa trên quy tắc và quy trình tin cậy.
- Các điều khiển vòng đời phiên (tiếp tục/nhánh) và các điều khiển vòng đời worktree nâng cao.
- Chi tiết về runtime MCP đầy đủ (transport/OAuth/đăng ký tài nguyên/polling).

Hãy xem giao thức hộp thư JSONL của nhóm trong repo này như một bản thực thi phục vụ giảng dạy, không phải là một khẳng định về bất kỳ chi tiết nội bộ sản xuất cụ thể nào.

## Bắt đầu nhanh

```sh
git clone https://github.com/shareAI-lab/learn-claude-code
cd learn-claude-code
pip install -r requirements.txt
cp .env.example .env   # Chỉnh sửa .env với ANTHROPIC_API_KEY của bạn

python agents/s01_agent_loop.py       # Bắt đầu tại đây
python agents/s12_worktree_task_isolation.py  # Điểm cuối của lộ trình tiến triển
python agents/s_full.py               # Bài học tổng hợp: kết hợp tất cả các cơ chế
```

### Nền tảng Web

Hình ảnh trực quan tương tác, sơ đồ từng bước, trình xem mã nguồn và tài liệu.

```sh
cd web && npm install && npm run dev   # http://localhost:3000
```

## Lộ trình học tập

```
Giai đoạn 1: VÒNG LẶP                  Giai đoạn 2: LẬP KẾ HOẠCH & KIẾN THỨC
====================                   ====================================
s01  Vòng lặp Agent          [1]     s03  TodoWrite               [5]
     while + stop_reason                  TodoManager + lời nhắc nhở
     |                                    |
     +-> s02  Sử dụng Công cụ     [4]     s04  Subagent             [5]
              bản đồ điều phối: tên->trình xử lý   messages[] mới cho mỗi con
                                               |
                                          s05  Kỹ năng              [5]
                                               SKILL.md qua tool_result
                                               |
                                          s06  Nén Ngữ cảnh         [5]
                                               nén 3 lớp

Giai đoạn 3: LƯU TRỮ                   Giai đoạn 4: NHÓM
====================                   =====================
s07  Nhiệm vụ                [8]     s09  Nhóm Agent              [9]
     CRUD dựa trên tệp + đồ thị phụ thuộc  đồng đội + hộp thư JSONL
     |                                    |
s08  Nhiệm vụ Nền            [6]     s10  Giao thức Nhóm          [12]
     luồng daemon + hàng đợi thông báo    tắt máy + phê duyệt kế hoạch FSM
                                          |
                                     s11  Agent Tự trị            [14]
                                          chu kỳ rảnh + tự nhận việc
                                     |
                                     s12  Cô lập Worktree         [16]
                                          phối hợp nhiệm vụ + các luồng thực thi cô lập tùy chọn

                                     [N] = số lượng công cụ
```

## Kiến trúc

```
learn-claude-code/
|
|-- agents/                        # Các bản thực thi tham chiếu bằng Python (s01-s12 + s_full)
|-- docs/{en,zh,ja,vi}/            # Tài liệu ưu tiên mô hình tư duy (4 ngôn ngữ)
|-- web/                           # Nền tảng học tập tương tác (Next.js)
|-- skills/                        # Các tệp kỹ năng cho s05
+-- .github/workflows/ci.yml      # CI: kiểm tra kiểu + build
```

## Tài liệu

Ưu tiên mô hình tư duy: vấn đề, giải pháp, sơ đồ ASCII, mã nguồn tối thiểu.
Có sẵn bằng [Tiếng Anh](./docs/en/) | [Tiếng Việt](./docs/vi/) | [Tiếng Trung](./docs/zh/) | [Tiếng Nhật](./docs/ja/).

| Phiên học | Chủ đề | Phương châm |
|-----------|--------|-------------|
| [s01](./docs/vi/s01-the-agent-loop.md) | Vòng lặp Agent | *Một vòng lặp & Bash là tất cả những gì bạn cần* |
| [s02](./docs/vi/s02-tool-use.md) | Sử dụng Công cụ | *Thêm một công cụ nghĩa là thêm một trình xử lý* |
| [s03](./docs/vi/s03-todo-write.md) | TodoWrite | *Một agent không có kế hoạch sẽ bị mất phương hướng* |
| [s04](./docs/vi/s04-subagent.md) | Subagent | *Chia nhỏ các nhiệm vụ lớn; mỗi nhiệm vụ con nhận một ngữ cảnh sạch* |
| [s05](./docs/vi/s05-skill-loading.md) | Kỹ năng | *Tải kiến thức khi cần, không phải tải trước* |
| [s06](./docs/vi/s06-context-compact.md) | Nén Ngữ cảnh | *Ngữ cảnh sẽ đầy; bạn cần một cách để tạo chỗ trống* |
| [s07](./docs/vi/s07-task-system.md) | Nhiệm vụ | *Chia nhỏ mục tiêu lớn thành các nhiệm vụ nhỏ, sắp xếp chúng, lưu vào đĩa* |
| [s08](./docs/vi/s08-background-tasks.md) | Nhiệm vụ Nền | *Chạy các thao tác chậm ở chế độ nền; agent tiếp tục suy nghĩ* |
| [s09](./docs/vi/s09-agent-teams.md) | Nhóm Agent | *Khi nhiệm vụ quá lớn cho một người, hãy ủy thác cho đồng đội* |
| [s10](./docs/vi/s10-team-protocols.md) | Giao thức Nhóm | *Đồng đội cần các quy tắc giao tiếp chung* |
| [s11](./docs/vi/s11-autonomous-agents.md) | Agent Tự trị | *Đồng đội quét bảng nhiệm vụ và tự nhận nhiệm vụ* |
| [s12](./docs/vi/s12-worktree-task-isolation.md) | Worktree + Cô lập Nhiệm vụ | *Mỗi người làm việc trong thư mục riêng của mình, không can thiệp lẫn nhau* |

## Bước tiếp theo -- từ thấu hiểu đến triển khai

Sau 12 phiên học, bạn đã hiểu rõ cách thức hoạt động của kỹ thuật harness. Có hai cách để áp dụng kiến thức đó vào thực tế:

### Kode Agent CLI -- CLI Coding Agent mã nguồn mở

> `npm i -g @shareai-lab/kode`

Hỗ trợ Skill & LSP, sẵn sàng cho Windows, có thể cắm với GLM / MiniMax / DeepSeek và các mô hình mở khác. Cài đặt và sử dụng ngay.

GitHub: **[shareAI-lab/Kode-cli](https://github.com/shareAI-lab/Kode-cli)**

### Kode Agent SDK -- Nhúng khả năng Agent vào ứng dụng của bạn

Claude Code Agent SDK chính thức giao tiếp với một quy trình CLI đầy đủ bên dưới -- mỗi người dùng đồng thời có nghĩa là một quy trình terminal riêng biệt. Kode SDK là một thư viện độc lập không có chi phí quy trình trên mỗi người dùng, có thể nhúng vào backend, tiện ích mở rộng trình duyệt, thiết bị nhúng hoặc bất kỳ runtime nào.

GitHub: **[shareAI-lab/Kode-agent-sdk](https://github.com/shareAI-lab/Kode-agent-sdk)**

---

## Repo chị em: từ *các phiên theo yêu cầu* đến *trợ lý luôn hoạt động*

Bộ harness mà repo này dạy mang tính chất **sử dụng-rồi-bỏ** -- mở terminal, giao nhiệm vụ cho agent, đóng lại khi xong, phiên tiếp theo bắt đầu mới hoàn toàn. Đó là mô hình của Claude Code.

[OpenClaw](https://github.com/openclaw/openclaw) đã chứng minh một khả năng khác: trên cùng một lõi agent, hai cơ chế harness biến agent từ "chạm vào để nó di chuyển" thành "nó tự thức dậy mỗi 30 giây để tìm việc":

- **Heartbeat** -- mỗi 30 giây harness gửi cho agent một tin nhắn để kiểm tra xem có việc gì cần làm không. Không có gì? Đi ngủ tiếp. Có việc? Hành động ngay lập tức.
- **Cron** -- agent có thể tự lên lịch các nhiệm vụ tương lai cho chính mình, được thực thi tự động khi đến thời điểm.

Thêm định tuyến IM đa kênh (WhatsApp / Telegram / Slack / Discord, hơn 13 nền tảng), bộ nhớ ngữ cảnh bền vững và hệ thống tính cách Soul, agent sẽ chuyển từ một công cụ dùng một lần thành một trợ lý AI cá nhân luôn hoạt động.

**[claw0](https://github.com/shareAI-lab/claw0)** là repo giảng dạy đi kèm của chúng tôi, tháo gỡ các cơ chế harness này từ đầu:

```
claw agent = lõi agent + heartbeat + cron + chat IM + bộ nhớ + soul
```

```
learn-claude-code                   claw0
(lõi harness agent:                 (harness chủ động luôn hoạt động:
 vòng lặp, công cụ, lập kế hoạch,     heartbeat, cron, các kênh IM,
 nhóm, cô lập worktree)              bộ nhớ, tính cách soul)
```

## Về chúng tôi
<img width="260" src="https://github.com/user-attachments/assets/fe8b852b-97da-4061-a467-9694906b5edf" /><br>

Quét bằng WeChat để theo dõi chúng tôi,
hoặc theo dõi trên X: [shareAI-Lab](https://x.com/baicai003)

## Giấy phép

MIT

---

**Agency đến từ mô hình. Harness làm cho agency trở thành hiện thực. Hãy xây dựng những bộ harness tuyệt vời. Mô hình sẽ làm phần còn lại.**

**Bash là tất cả những gì bạn cần. Agent thực thụ là tất cả những gì vũ trụ cần.**
