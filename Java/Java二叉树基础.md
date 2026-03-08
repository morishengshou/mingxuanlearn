下面给出从“最小可用”到“稍完整”的几种 Java 二叉树实现方式。你可以按需要裁剪或扩展。

一、最小可用：节点定义 + 基本遍历
- 适合学习结构与遍历顺序
- 不包含插入规则（例如 BST 的有序插入）

```java
public class BinaryTree<T> {
    public static class Node<T> {
        public T val;
        public Node<T> left, right;
        public Node(T val) { this.val = val; }
    }

    public Node<T> root;

    // 先序遍历：根-左-右
    public void preorder(Node<T> n, java.util.function.Consumer<T> visit) {
        if (n == null) return;
        visit.accept(n.val);
        preorder(n.left, visit);
        preorder(n.right, visit);
    }

    // 中序遍历：左-根-右
    public void inorder(Node<T> n, java.util.function.Consumer<T> visit) {
        if (n == null) return;
        inorder(n.left, visit);
        visit.accept(n.val);
        inorder(n.right, visit);
    }

    // 后序遍历：左-右-根
    public void postorder(Node<T> n, java.util.function.Consumer<T> visit) {
        if (n == null) return;
        postorder(n.left, visit);
        postorder(n.right, visit);
        visit.accept(n.val);
    }

    // 层序遍历：按层访问
    public void levelOrder(java.util.function.Consumer<T> visit) {
        if (root == null) return;
        java.util.ArrayDeque<Node<T>> q = new java.util.ArrayDeque<>();
        q.add(root);
        while (!q.isEmpty()) {
            Node<T> cur = q.poll();
            visit.accept(cur.val);
            if (cur.left != null) q.add(cur.left);
            if (cur.right != null) q.add(cur.right);
        }
    }
}
```

二、二叉查找树（BST）：带有序插入/查找/删除
- 对可比较类型（Comparable）按键有序存储
- 平均复杂度：查找/插入/删除为 O(log n)，最坏 O(n)（退化成链）

```java
public class BST<K extends Comparable<K>, V> {
    public static class Node<K, V> {
        K key;
        V val;
        Node<K, V> left, right;
        Node(K k, V v) { key = k; val = v; }
    }

    private Node<K, V> root;
    private int size;

    public int size() { return size; }
    public boolean isEmpty() { return size == 0; }

    // 查找
    public V get(K key) {
        Node<K, V> x = root;
        while (x != null) {
            int cmp = key.compareTo(x.key);
            if (cmp == 0) return x.val;
            x = (cmp < 0) ? x.left : x.right;
        }
        return null;
    }

    // 插入（存在则更新值）
    public void put(K key, V val) {
        root = put(root, key, val);
    }
    private Node<K, V> put(Node<K, V> x, K key, V val) {
        if (x == null) { size++; return new Node<>(key, val); }
        int cmp = key.compareTo(x.key);
        if (cmp < 0) x.left = put(x.left, key, val);
        else if (cmp > 0) x.right = put(x.right, key, val);
        else x.val = val; // 覆盖
        return x;
    }

    // 最小/最大键
    public K minKey() { return min(root).key; }
    public K maxKey() { return max(root).key; }
    private Node<K, V> min(Node<K, V> x) {
        if (x == null) throw new IllegalStateException("empty");
        while (x.left != null) x = x.left;
        return x;
    }
    private Node<K, V> max(Node<K, V> x) {
        if (x == null) throw new IllegalStateException("empty");
        while (x.right != null) x = x.right;
        return x;
    }

    // 删除最小/最大
    public void deleteMin() { root = deleteMin(root); }
    private Node<K, V> deleteMin(Node<K, V> x) {
        if (x == null) return null;
        if (x.left == null) { size--; return x.right; }
        x.left = deleteMin(x.left);
        return x;
    }
    public void deleteMax() { root = deleteMax(root); }
    private Node<K, V> deleteMax(Node<K, V> x) {
        if (x == null) return null;
        if (x.right == null) { size--; return x.left; }
        x.right = deleteMax(x.right);
        return x;
    }

    // 按键删除
    public void delete(K key) { root = delete(root, key); }
    private Node<K, V> delete(Node<K, V> x, K key) {
        if (x == null) return null;
        int cmp = key.compareTo(x.key);
        if (cmp < 0) x.left = delete(x.left, key);
        else if (cmp > 0) x.right = delete(x.right, key);
        else {
            // 命中：三种情况
            if (x.left == null) { size--; return x.right; }
            if (x.right == null) { size--; return x.left; }
            // 两个孩子：用后继替换（Hibbard deletion）
            Node<K, V> t = x;
            x = min(t.right);                  // 后继
            x.right = deleteMin(t.right);      // 删掉后继
            x.left = t.left;
            // size 在 deleteMin 已经减 1，这里不需要再改
        }
        return x;
    }

    // 中序遍历（从小到大）
    public void inorder(java.util.function.BiConsumer<K, V> visit) {
        inorder(root, visit);
    }
    private void inorder(Node<K, V> x, java.util.function.BiConsumer<K, V> visit) {
        if (x == null) return;
        inorder(x.left, visit);
        visit.accept(x.key, x.val);
        inorder(x.right, visit);
    }
}
```

三、构建与常用操作示例
```java
public class Demo {
    public static void main(String[] args) {
        // 1) 原始二叉树结构（不保证有序）
        BinaryTree<Integer> bt = new BinaryTree<>();
        bt.root = new BinaryTree.Node<>(1);
        bt.root.left = new BinaryTree.Node<>(2);
        bt.root.right = new BinaryTree.Node<>(3);
        bt.inorder(bt.root, System.out::println); // 2 1 3

        // 2) 二叉查找树（有序）
        BST<Integer, String> bst = new BST<>();
        bst.put(5, "A");
        bst.put(2, "B");
        bst.put(8, "C");
        bst.put(5, "A2"); // 更新
        System.out.println(bst.get(2)); // B
        bst.inorder((k, v) -> System.out.println(k + " => " + v)); // 2,5,8

        bst.delete(5);
        bst.inorder((k, v) -> System.out.println(k + " => " + v)); // 2,8
    }
}
```

四、扩展方向
- 平衡二叉搜索树：AVL、红黑树（Java 的 TreeMap/TreeSet 即为红黑树）。
- 序列化/反序列化：层序数组表示、前序+空标记等。
- 非递归遍历：使用显式栈；大树能避免深递归栈溢出。
- 线程安全：外部加锁或使用并发友好的结构（通常使用现成库）。

如果你有特定需求（支持重复键、比较器、自平衡、迭代器等），告诉我我可以按你的场景给出定制实现。